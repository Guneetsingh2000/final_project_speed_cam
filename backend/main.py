# backend/main.py

import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from .speed import analyze_video

app = FastAPI(title="AI Speed Camera Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "AI Speed Camera Backend running"}


@app.post("/analyze-video")
async def analyze_video_endpoint(
    file: UploadFile = File(...),
    speed_limit_kmh: float = Form(60.0),
    grace_kmh: float = Form(5.0),
    meters_per_pixel: float = Form(0.05),
    frame_stride: int = Form(3),
):
    """
    Receives full video from Streamlit frontend, runs YOLO + tracking + speed,
    and returns JSON summary and encoded annotated video.
    """
    # Save uploaded video to a temporary file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        summary = analyze_video(
            video_path=tmp_path,
            speed_limit_kmh=speed_limit_kmh,
            grace_kmh=grace_kmh,
            meters_per_pixel=meters_per_pixel,
            frame_stride=frame_stride,
        )
        return summary
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)



