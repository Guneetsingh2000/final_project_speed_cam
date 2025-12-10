# backend/utils.py

import os
import csv
from typing import Optional, Dict

import smtplib
import ssl
from email.message import EmailMessage

# Base directory = project root
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Simple CSV database of plates → owners
PLATE_DB_PATH = os.path.join(BASE_DIR, "data", "plate_owners.csv")

# Email config (set these in your terminal or .env if you want real emails)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
EMAIL_USER = os.getenv("EMAIL_USER")  # your Gmail
EMAIL_PASS = os.getenv("EMAIL_PASS")  # app password


def lookup_owner(plate_text: Optional[str]) -> Optional[Dict]:
    """
    Look up owner info for a plate from data/plate_owners.csv.
    CSV format:
        plate,owner,email
        ABC123,John Doe,john@example.com
    """
    if not plate_text:
        return None
    if not os.path.exists(PLATE_DB_PATH):
        print(f"[WARN] Plate DB not found at {PLATE_DB_PATH}")
        return None

    plate_upper = plate_text.upper().strip()

    with open(PLATE_DB_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("plate", "").upper().strip() == plate_upper:
                return {
                    "plate": plate_upper,
                    "owner": row.get("owner", ""),
                    "email": row.get("email", ""),
                }
    return None


def send_violation_email(track, speed_limit_kmh: float, grace_kmh: float) -> None:
    """
    Real-ish email sending using SMTP.
    If EMAIL_USER or EMAIL_PASS or owner email are missing, just logs to console.
    """
    info = track.owner_info or {}
    to_email = info.get("email")

    print("\n=== OVERSPEED EVENT ===")
    print(f"Track ID    : {track.track_id}")
    print(f"Class       : {track.cls_id}")
    print(f"Max speed   : {track.max_speed_kmh:.2f} km/h")
    print(f"Speed limit : {speed_limit_kmh} km/h (+{grace_kmh} grace)")
    print(f"Plate       : {track.plate_text}")
    print(f"Owner info  : {info}")

    if not EMAIL_USER or not EMAIL_PASS or not to_email:
        print("[INFO] EMAIL_USER/EMAIL_PASS or owner email not set. Skipping real email send.")
        return

    subject = f"[Speed Camera] Overspeed warning for plate {track.plate_text}"
    body = (
        f"Vehicle with plate {track.plate_text} exceeded the speed limit.\n\n"
        f"Track ID: {track.track_id}\n"
        f"Class: {track.cls_id}\n"
        f"Max speed: {track.max_speed_kmh:.2f} km/h\n"
        f"Limit: {speed_limit_kmh} km/h (+{grace_kmh} grace)\n"
        f"Owner: {info.get('owner', 'Unknown')}\n"
    )

    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"[EMAIL] Sent overspeed email to {to_email}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
