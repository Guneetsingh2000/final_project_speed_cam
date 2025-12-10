from ultralytics import YOLO
from .config import MODEL_PATH

# COCO vehicle class IDs
VEHICLE_IDS = {2, 3, 5, 7}  # car, motorcycle, bus, truck


class VehicleDetector:
    def __init__(self):
        self.model = YOLO(MODEL_PATH)

    def detect(self, frame):
        results = self.model.predict(frame, verbose=False)[0]
        detections = []

        for box in results.boxes:
            cls = int(box.cls[0])
            if cls not in VEHICLE_IDS:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])

            detections.append({
                "bbox": (x1, y1, x2, y2),
                "cls": cls,
                "conf": conf
            })

        return detections


detector = VehicleDetector()


