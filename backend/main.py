# backend/main.py

from typing import Dict, Any
from .speed import run_speed_estimation


def analyze_video_file(
    video_path: str,
    speed_limit_kmh: float = 60.0,
    grace_kmh: float = 5.0,
) -> Dict[str, Any]:
    """
    Wrapper that calls the speed estimation pipeline and returns results.

    This is what the Streamlit frontend will import and call directly.
    """
    results = run_speed_estimation(
        video_path=video_path,
        speed_limit_kmh=speed_limit_kmh,
        grace_kmh=grace_kmh,
    )
    return results




