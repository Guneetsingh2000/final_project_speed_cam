# backend/main.py

import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# ✅ Adjust these imports to match your existing files
from . import speed  # your speed processing module
# If you already have typed schemas, you can import them instead of using dict


# === Paths ===
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="SpeedCam Backend",
    description="YOLO + tracking speed estimation backend for the Streamlit frontend.",
    version="1.0.0",
)

# === CORS so Streamlit Cloud / localhost can talk to this ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # you can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "SpeedCam FastAPI backend running.",
    }


@app.post("/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    """
    Receive an uploaded video, save to temp, run the speed pipeline,
    and return JSON results.
    """

    # 1) Save upload to a temporary file
    ext = Path(file.filename).suffix or ".mp4"
    tmp_name = f"{uuid.uuid4().hex}{ext}"
    tmp_path = UPLOAD_DIR / tmp_name

    with tmp_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # 2) Run your existing speed pipeline
    #    🔴 IMPORTANT: change `run_speed_estimation` to whatever function
    #    you already use that takes a video path and returns a dict.
    #    For example, if you had speed.process_video(tmp_path) use that instead.
    try:
        result = speed.run_speed_estimation(str(tmp_path))
        # expected shape (example):
        # {
        #   "summary": {...},
        #   "overspeed_events": [...],
        #   "within_limit": [...]
        # }
    except Exception as e:
        # Clean up before raising
        if tmp_path.exists():
            tmp_path.unlink()
        return {"status": "error", "detail": str(e)}

    # 3) Clean up temporary file
    if tmp_path.exists():
        tmp_path.unlink()

    # 4) Return JSON
    return {
        "status": "ok",
        "data": result,
    }


# Optional: endpoint to just check health
@app.get("/health")
def health():
    return {"status": "healthy"}




