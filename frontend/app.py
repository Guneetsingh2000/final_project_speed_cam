# frontend/app.py

import json
import requests
import streamlit as st

DEFAULT_BACKEND_URL = "http://localhost:8000/analyze_video"


def call_backend(backend_url: str, video_bytes: bytes, filename: str):
    """Send video file to FastAPI backend and return JSON response."""
    files = {"file": (filename, video_bytes, "video/mp4")}
    try:
        resp = requests.post(backend_url, files=files, timeout=600)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling backend: {e}")
        return None

    try:
        return resp.json()
    except Exception as e:
        st.error(f"Error parsing backend response as JSON: {e}")
        return None


def main():
    st.set_page_config(page_title="AI Speed Camera", layout="wide")

    st.title("AI-Based Vehicle Speed Monitoring System")
    st.write(
        "Upload a road traffic video and this app will detect vehicles, "
        "estimate their speeds using computer vision, and flag overspeeding events."
    )

    # Sidebar – settings
    with st.sidebar:
        st.header("Backend Settings")
        backend_url = st.text_input(
            "Backend /analyze_video URL",
            value=DEFAULT_BACKEND_URL,
            help="Make sure your FastAPI backend is running on this URL.",
        )

        st.markdown("---")
        st.header("Instructions")
        st.write(
            "1. Start the backend (FastAPI)\n"
            "2. Upload a video below\n"
            "3. Click **Run Analysis**"
        )

    # File upload
    uploaded_video = st.file_uploader(
        "Upload traffic video (.mp4, .mov, .avi, .mkv)",
        type=["mp4", "mov", "avi", "mkv"],
    )

    if uploaded_video is None:
        st.info("Please upload a video to begin.")
        return

    # Show video preview
    st.video(uploaded_video)

    run_clicked = st.button("Run Analysis")

    if not run_clicked:
        return

    with st.spinner("Sending video to backend and analyzing..."):
        video_bytes = uploaded_video.read()
        result = call_backend(backend_url.strip(), video_bytes, uploaded_video.name)

    if result is None:
        st.stop()

    if result.get("status") != "ok":
        st.error(f"Backend returned an error: {result}")
        st.stop()

    data = result.get("data", {})

    summary = data.get("summary_stats", {})
    overspeed_events = data.get("overspeed_events", [])
    within_limit = data.get("within_limit", [])

    # === Summary ===
    st.subheader("Summary Statistics")
    if summary:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total vehicles", summary.get("num_vehicles", 0))
        c2.metric("Overspeeding", summary.get("num_overspeed", 0))
        c3.metric("Within limit", summary.get("num_within_limit", 0))

        st.write(
            f"Speed limit: **{summary.get('speed_limit_kmh', 0)} km/h**  "
            f"(grace: **{summary.get('grace_kmh', 0)} km/h**)"
        )
    else:
        st.write("No summary statistics returned from backend.")

    st.markdown("---")

    # === Overspeed table ===
    st.subheader("Overspeeding Vehicles")
    if overspeed_events:
        st.table(overspeed_events)
    else:
        st.write("No overspeed events detected.")

    # === Within-limit table ===
    st.subheader("Within-Limit Vehicles")
    if within_limit:
        st.table(within_limit)
    else:
        st.write("No vehicles within limit or insufficient tracking data.")

    # === Raw JSON (debug) ===
    with st.expander("Raw JSON response (debug)"):
        st.code(json.dumps(result, indent=2), language="json")


if __name__ == "__main__":
    main()
