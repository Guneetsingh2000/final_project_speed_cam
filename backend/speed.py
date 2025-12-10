# backend/speed.py

import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
from typing import Dict, Any, List


def load_detector(model_dir: str = "models") -> YOLO:
    """
    Load YOLO model for vehicle detection.
    Tries car_detector_fast.pt first, then falls back to yolov8n.pt.
    """
    model_path = None

    # Try custom model first
    custom = Path(model_dir) / "car_detector_fast.pt"
    if custom.exists():
        model_path = str(custom)
    else:
        # Fallback – expects yolov8n.pt in models/ or downloads default
        tiny = Path(model_dir) / "yolov8n.pt"
        if tiny.exists():
            model_path = str(tiny)
        else:
            # Let ultralytics download the default yolov8n if nothing found
            model_path = "yolov8n.pt"

    model = YOLO(model_path)
    return model


def run_speed_estimation(
    video_path: str,
    speed_limit_kmh: float = 60.0,
    grace_kmh: float = 5.0,
    px_to_m_factor: float = 0.05,
) -> Dict[str, Any]:
    """
    Estimate vehicle speeds from a video using YOLO tracking.

    Assumptions:
    - Camera is roughly fixed.
    - Vertical movement in pixels ~ distance along the road.
    - px_to_m_factor: meters per pixel (tuned by calibration).
    """

    video_path = str(video_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if fps <= 0:
        fps = 30.0  # safe default

    model = load_detector()

    # track_id -> info
    tracks: Dict[int, Dict[str, Any]] = {}
    frame_idx = 0

    # Classes for vehicles in COCO: car=2, bus=5, truck=7, motorcycle=3
    vehicle_classes = {2, 3, 5, 7}

    # Use YOLO tracking in streaming mode
    for result in model.track(
        source=video_path,
        stream=True,
        verbose=False,
        persist=True,
    ):
        frame_idx += 1

        if result.boxes is None or result.boxes.id is None:
            continue

        ids = result.boxes.id.cpu().numpy().astype(int)
        xyxy = result.boxes.xyxy.cpu().numpy()
        clses = result.boxes.cls.cpu().numpy().astype(int)

        for tid, box, cls_id in zip(ids, xyxy, clses):
            if cls_id not in vehicle_classes:
                continue

            x1, y1, x2, y2 = box.tolist()
            cy = (y1 + y2) / 2.0  # vertical center

            info = tracks.get(tid, {
                "last_y": cy,
                "last_frame": frame_idx,
                "max_speed_kmh": 0.0,
                "class_id": int(cls_id),
            })

            # compute speed from movement between frames
            prev_frame = info["last_frame"]
            prev_y = info["last_y"]
            dt_frames = frame_idx - prev_frame

            if dt_frames > 0:
                dt_s = dt_frames / fps
                dy_px = abs(cy - prev_y)
                dist_m = dy_px * px_to_m_factor
                speed_m_s = dist_m / dt_s if dt_s > 0 else 0.0
                speed_kmh = speed_m_s * 3.6
                if speed_kmh > info["max_speed_kmh"]:
                    info["max_speed_kmh"] = speed_kmh

            info["last_y"] = cy
            info["last_frame"] = frame_idx
            tracks[tid] = info

    # Build result tables
    overspeed_events: List[Dict[str, Any]] = []
    within_limit: List[Dict[str, Any]] = []

    limit_with_grace = speed_limit_kmh + grace_kmh

    for tid, info in tracks.items():
        max_speed = float(info["max_speed_kmh"])
        row = {
            "track_id": tid,
            "vehicle_class": info["class_id"],
            "max_speed_kmh": round(max_speed, 2),
            "speed_limit_kmh": speed_limit_kmh,
            "grace_kmh": grace_kmh,
        }
        if max_speed > limit_with_grace:
            overspeed_events.append(row)
        else:
            within_limit.append(row)

    summary = {
        "num_vehicles": len(tracks),
        "num_overspeed": len(overspeed_events),
        "num_within_limit": len(within_limit),
        "speed_limit_kmh": speed_limit_kmh,
        "grace_kmh": grace_kmh,
    }

    return {
        "summary_stats": summary,
        "overspeed_events": overspeed_events,
        "within_limit": within_limit,
    }

