from pydantic import BaseModel
from typing import List

class CalibrationRequest(BaseModel):
    video_id: str
    lane_width_m: float
    fps: float
    p1_x: float
    p1_y: float
    p2_x: float
    p2_y: float

class FrameDetectionRequest(BaseModel):
    frame_id: int
    video_id: str
    speed_limit_kmh: float
    image_b64: str

class VehicleResult(BaseModel):
    track_id: int
    speed_kmh: float
    category: str
    risk_reason: str

class FrameDetectionResponse(BaseModel):
    frame_id: int
    results: List[VehicleResult]

