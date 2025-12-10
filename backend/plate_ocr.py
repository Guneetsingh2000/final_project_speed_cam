# backend/plate_ocr.py

from typing import Optional
import numpy as np

def read_plate_text_from_crop(plate_crop_bgr: np.ndarray) -> str:
    """
    Stub implementation for demo:
    - No EasyOCR
    - Always returns empty string
    Explain in report that plate OCR is a future improvement.
    """
    if plate_crop_bgr is None or plate_crop_bgr.size == 0:
        return ""
    return ""  # no OCR – just a placeholder


def read_plate_text(image_bgr: Optional[object]) -> str:
    """
    Backwards-compatible wrapper.
    """
    if isinstance(image_bgr, np.ndarray):
        return read_plate_text_from_crop(image_bgr)
    return ""


