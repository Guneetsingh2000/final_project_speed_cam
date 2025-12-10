# backend/speed.py

import os
import math
import base64
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import cv2
from ultralytics import YOLO

from .utils import lookup_owner, send_violation_email
from .plate_ocr import read_plate_text_from_crop

# Base dir = project root (.. from backend/)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Path to your YOLO model (you said this file exists & works)
MODEL_PATH = os.path.join(BASE_DIR, "yolov8n.pt")

# Classes in your general YOLO model (COCO-style)
# We'll treat these as "vehicles" for tracking:
# 2 = car, 3 = motorcycle, 5 = bus, 7 = truck, etc. (depends on your model)
VEHICLE_CLASS_IDS = {2, 3, 5, 7}  # adjust if needed

# Minimum pixel movement to consider for speed (to ignore tiny jitter)
MIN_PIXELS_FOR_SPEED = 3.0

# Hard cap on speed to avoid insane spikes (km/h)
MAX_REASONABLE_SPEED = 180.0


@dataclass
class Track:
    track_id: int
    cls_id: int
    last_center: Optional[Tuple[float, float]] = None  # (x, y)
    last_frame_idx: Optional[int] = None
    speeds_kmh: List[float] = field(default_factory=list)
    max_speed_kmh: float = 0.0
    status: str = "unknown"  # within_limit, grace, overspeed
    plate_text: Optional[str] = None
    owner_info: Optional[Dict] = None
    overspeed_handled: bool = False


def load_vehicle_model() -> YOLO:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"YOLO model not found at: {MODEL_PATH}")
    return YOLO(MODEL_PATH)


def estimate_speed_kmh(pix_dist: float, dt: float, meters_per_pixel: float) -> float:
    if dt <= 0:
        return 0.0
    meters = pix_dist * meters_per_pixel
    mps = meters / dt
    return mps * 3.6  # m/s → km/h


def analyze_video(
    video_path: str,
    speed_limit_kmh: float = 60.0,
    grace_kmh: float = 5.0,
    meters_per_pixel: float = 0.05,
    frame_stride: int = 3,
) -> Dict:
    """
    Core pipeline:
      - open video
      - get FPS from the video (time comes from frames, not CPU time)
      - run YOLO every N frames
      - naive nearest-neighbor tracking
      - estimate speed based on center movement & FPS
      - classify status vs speed limit (+ grace)
      - OCR plates (if EasyOCR available) & overspeed email
      - produce preview frames and annotated video
    """
    model = load_vehicle_model()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    # 🔹 Real timing based on FPS
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 1e-3:
        fps = 30.0  # fallback if metadata missing
    print(f"[INFO] Using FPS={fps:.2f} for speed calculation")

    frame_idx = 0
    next_track_id = 1
    tracks: List[Track] = []

    start_time_wall = time.time()
    preview_frames_b64: List[str] = []
    max_preview_frames = 5

    limit = speed_limit_kmh
    grace_limit = speed_limit_kmh + grace_kmh

    # Video writer for annotated video
    annotated_video_path = os.path.join(BASE_DIR, "runs", "last_annotated.mp4")
    writer = None
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    annotated_fps = fps  # keep same fps for nicer playback if possible

    os.makedirs(os.path.dirname(annotated_video_path), exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % frame_stride != 0:
            continue

        results = model.predict(
            source=frame,
            imgsz=640,
            conf=0.3,
            verbose=False,
            device="cpu",
        )

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            continue

        detections = []  # (center, box_xyxy, cls_id, tr, speed_now)

        for b in boxes:
            cls_id = int(b.cls.item())

            # keep only vehicles
            if cls_id not in VEHICLE_CLASS_IDS:
                continue

            x1, y1, x2, y2 = b.xyxy[0].tolist()
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            center = (cx, cy)

            # ---------- Nearest-neighbor track association ----------
            best_track = None
            best_dist = float("inf")
            for tr in tracks:
                if tr.cls_id != cls_id:
                    continue
                if tr.last_center is None:
                    continue
                dist = math.dist(center, tr.last_center)
                if dist < best_dist:
                    best_dist = dist
                    best_track = tr

            if best_track is not None and best_dist < 100:
                tr = best_track
            else:
                tr = Track(track_id=next_track_id, cls_id=cls_id)
                next_track_id += 1
                tracks.append(tr)

            # ---------- Speed estimation based on FPS + frame index ----------
            speed_now = 0.0
            if tr.last_center is not None and tr.last_frame_idx is not None:
                pix_dist = math.dist(center, tr.last_center)
                frame_delta = frame_idx - tr.last_frame_idx

                if frame_delta > 0 and pix_dist >= MIN_PIXELS_FOR_SPEED:
                    dt = (frame_delta * 1.0) / fps  # seconds between samples
                    speed_now = estimate_speed_kmh(pix_dist, dt, meters_per_pixel)

                    # clamp insane spikes
                    if speed_now > MAX_REASONABLE_SPEED:
                        speed_now = MAX_REASONABLE_SPEED

                    tr.speeds_kmh.append(speed_now)
                    if speed_now > tr.max_speed_kmh:
                        tr.max_speed_kmh = speed_now

            tr.last_center = center
            tr.last_frame_idx = frame_idx

            # ---------- Classify status ----------
            if tr.max_speed_kmh > grace_limit:
                tr.status = "overspeed"
            elif tr.max_speed_kmh > limit:
                tr.status = "grace"
            elif tr.max_speed_kmh > 0:
                tr.status = "within_limit"

            # ---------- OCR plates for ALL vehicles (once per track) ----------
            if tr.plate_text is None and tr.status in {"within_limit", "grace", "overspeed"}:
                h, w = frame.shape[:2]
                ix1, iy1, ix2, iy2 = map(int, [x1, y1, x2, y2])
                ix1 = max(0, min(ix1, w - 1))
                ix2 = max(0, min(ix2, w - 1))
                iy1 = max(0, min(iy1, h - 1))
                iy2 = max(0, min(iy2, h - 1))
                box_h = iy2 - iy1
                plate_y1 = int(iy1 + 0.7 * box_h)
                plate_y2 = iy2
                plate_crop = frame[plate_y1:plate_y2, ix1:ix2]

                plate_text = (
                    read_plate_text_from_crop(plate_crop)
                    if plate_crop is not None and plate_crop.size > 0
                    else ""
                )
                tr.plate_text = plate_text or None
                tr.owner_info = lookup_owner(plate_text) if plate_text else None

            # ---------- Email only for overspeed ----------
            if tr.status == "overspeed" and not tr.overspeed_handled:
                tr.overspeed_handled = True
                send_violation_email(tr, speed_limit_kmh, grace_kmh)

            detections.append((center, (x1, y1, x2, y2), cls_id, tr, speed_now))

        # ---------- Draw annotated frame ----------
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        for center, box_xyxy, cls_id, tr, speed_now in detections:
            x1, y1, x2, y2 = map(int, box_xyxy)

            # Color by status
            color = (0, 255, 0)      # green = within limit
            if tr.status == "overspeed":
                color = (0, 0, 255)  # red
            elif tr.status == "grace":
                color = (0, 255, 255)  # yellow

            thickness = 2 if tr.status != "overspeed" else 3
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

            label = f"ID {tr.track_id} cls {cls_id} {speed_now:.1f} km/h"
            cv2.putText(
                annotated,
                label,
                (x1, max(0, y1 - 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )

            if tr.status == "overspeed":
                cv2.putText(
                    annotated,
                    "OVERSPEED",
                    (x1, min(h - 10, y2 + 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            # Plate region box
            box_h = y2 - y1
            plate_y1 = int(y1 + 0.7 * box_h)
            plate_y2 = y2
            cv2.rectangle(
                annotated,
                (x1, plate_y1),
                (x2, plate_y2),
                (255, 0, 0),
                2,
            )

            if tr.plate_text:
                cv2.putText(
                    annotated,
                    f"Plate: {tr.plate_text}",
                    (x1, min(h - 10, y2 + 40)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

        # Initialize video writer on first annotated frame
        if writer is None:
            height, width = annotated.shape[:2]
            writer = cv2.VideoWriter(
                annotated_video_path,
                fourcc,
                annotated_fps,
                (width, height),
            )

        if writer is not None:
            writer.write(annotated)

        # Keep a few preview frames as JPGs (for Streamlit image gallery)
        if len(preview_frames_b64) < max_preview_frames:
            success, buf = cv2.imencode(".jpg", annotated)
            if success:
                b64 = base64.b64encode(buf.tobytes()).decode("ascii")
                preview_frames_b64.append(b64)

    cap.release()
    if writer is not None:
        writer.release()

    total_time_wall = time.time() - start_time_wall

    overspeed_events = []
    grace_events = []
    ok_events = []
    all_speeds = []

    for tr in tracks:
        if tr.max_speed_kmh <= 0:
            continue
        all_speeds.append(round(tr.max_speed_kmh, 2))

        if tr.status == "overspeed":
            overspeed_events.append(tr)
        elif tr.status == "grace":
            grace_events.append(tr)
        elif tr.status == "within_limit":
            ok_events.append(tr)

    def track_to_dict(tr: Track) -> Dict:
        return {
            "track_id": tr.track_id,
            "class": tr.cls_id,
            "max_speed_kmh": round(tr.max_speed_kmh, 2),
            "status": tr.status,
            "plate_text": tr.plate_text,
            "owner_info": tr.owner_info,
        }

    annotated_video_b64 = None
    if os.path.exists(annotated_video_path):
        with open(annotated_video_path, "rb") as f:
            annotated_video_b64 = base64.b64encode(f.read()).decode("ascii")

    summary = {
        "speed_limit_kmh": speed_limit_kmh,
        "grace_kmh": grace_kmh,
        "meters_per_pixel": meters_per_pixel,
        "frame_stride": frame_stride,
        "total_tracks": len([t for t in tracks if t.max_speed_kmh > 0]),
        "overspeed_count": len(overspeed_events),
        "grace_count": len(grace_events),
        "within_limit_count": len(ok_events),
        "overspeed_vehicles": [track_to_dict(t) for t in overspeed_events],
        "grace_vehicles": [track_to_dict(t) for t in grace_events],
        "within_limit_vehicles": [track_to_dict(t) for t in ok_events],
        "processing_time_sec": round(total_time_wall, 2),
        "preview_frames_b64": preview_frames_b64,
        "all_speeds_kmh": all_speeds,
        "annotated_video_b64": annotated_video_b64,
    }

    return summary





def update_speed(video_id, track_id, frame_id, center, calib):
    HISTORY[video_id][track_id].append((frame_id, center, time()))
    hist = HISTORY[video_id][track_id]

    if len(hist) < 2:
        return None

    (f1, p1, t1), (f2, p2, t2) = hist[-2:]

    return estimate_speed(p1, p2, t2 - t1, calib)
