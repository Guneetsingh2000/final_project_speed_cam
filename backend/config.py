# backend/config.py

import os

# Project root = .../final_project_speed_cam
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to YOLO model (you said it's here)
YOLO_MODEL_PATH = os.path.join(PROJECT_ROOT, "yolov8n.pt")

# Where to save annotated outputs
RUNS_DIR = os.path.join(PROJECT_ROOT, "runs_car_dataset")
os.makedirs(RUNS_DIR, exist_ok=True)

# (Optional) Data dir for plate owner CSV
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
