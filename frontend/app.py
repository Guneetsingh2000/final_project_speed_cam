import base64
import requests
import streamlit as st

# 🔗 Backend URL (FastAPI)
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Speed Camera Demo",
    layout="wide",
)

st.title("🚔 AI Speed Camera Demo")

st.write(
    "This app sends a road video to a FastAPI backend that:\n"
    "- Detects vehicles using a YOLO model\n"
    "- Tracks them across frames and estimates speed\n"
    "- Classifies vehicles as **within limit**, **grace**, or **overspeed**\n"
    "- (Optional) Tries to read plates if OCR is available\n"
)

# ------------------------------
# Sidebar: parameters
# ------------------------------
st.sidebar.header("Speed Settings")

speed_limit = st.sidebar.number_input(
    "Speed limit (km/h)", min_value=10.0, max_value=200.0, value=60.0, step=5.0
)
grace = st.sidebar.number_input(
    "Grace over limit (km/h)", min_value=0.0, max_value=50.0, value=5.0, step=1.0
)
meters_per_pixel = st.sidebar.number_input(
    "Meters per pixel (calibration)",
    min_value=0.001,
    max_value=1.0,
    value=0.05,  # tweak this if speeds look too high/low
    step=0.01,
)
frame_stride = st.sidebar.number_input(
    "Frame stride (process every Nth frame)",
    min_value=1,
    max_value=10,
    value=3,
    step=1,
)

# ------------------------------
# Video upload
# ------------------------------
st.subheader("Upload Video")

uploaded_video = st.file_uploader(
    "Upload a road video (MP4, MOV, AVI, MKV)",
    type=["mp4", "mov", "avi", "mkv"],
)

if uploaded_video is not None:
    st.info("Video uploaded. Click **Analyze video** to start.")
    st.write(f"**Filename:** {uploaded_video.name}")
else:
    st.info("Please upload a video to enable analysis.")

analyze_clicked = st.button("Analyze video")

# ------------------------------
# Main logic
# ------------------------------
if analyze_clicked:
    if uploaded_video is None:
        st.error("No video uploaded. Please upload a video first.")
    else:
        with st.spinner("Sending video to backend and running analysis..."):
            files = {
                "file": (uploaded_video.name, uploaded_video, uploaded_video.type)
            }
            data = {
                "speed_limit_kmh": str(speed_limit),
                "grace_kmh": str(grace),
                "meters_per_pixel": str(meters_per_pixel),
                "frame_stride": str(frame_stride),
            }

            try:
                resp = requests.post(
                    f"{BACKEND_URL}/analyze-video",
                    files=files,
                    data=data,
                    timeout=600,
                )
            except Exception as e:
                st.error(f"Error contacting backend: {e}")
            else:
                if resp.status_code != 200:
                    st.error(f"Backend error: {resp.status_code} - {resp.text}")
                else:
                    result = resp.json()
                    st.success("Analysis complete!")

                    # Optional raw JSON
                    if st.checkbox("Show raw JSON response from backend"):
                        st.json(result)

                    # ------------------------------
                    # Summary metrics
                    # ------------------------------
                    st.subheader("Summary")

                    col1, col2, col3 = st.columns(3)
                    col1.metric(
                        "Total Vehicles Tracked",
                        result.get("total_tracks", 0),
                    )
                    col2.metric(
                        "Overspeed Vehicles",
                        result.get("overspeed_count", 0),
                    )
                    col3.metric(
                        "Grace Vehicles",
                        result.get("grace_count", 0),
                    )

                    col4, col5 = st.columns(2)
                    col4.metric(
                        "Within Limit Vehicles",
                        result.get("within_limit_count", 0),
                    )
                    col5.metric(
                        "Processing Time (sec)",
                        result.get("processing_time_sec", 0),
                    )

                    # ------------------------------
                    # Annotated video
                    # ------------------------------
                    annotated_video_b64 = result.get("annotated_video_b64")
                    if annotated_video_b64:
                        st.subheader("Annotated Video")
                        try:
                            video_bytes = base64.b64decode(annotated_video_b64)
                            st.video(video_bytes)
                        except Exception as e:
                            st.warning(f"Could not decode annotated video: {e}")
                    else:
                        st.info("No annotated video returned from backend.")

                    # ------------------------------
                    # Preview frames (simple gallery)
                    # ------------------------------
                    preview_frames_b64 = result.get("preview_frames_b64", [])
                    if preview_frames_b64:
                        st.subheader("Preview Frames (annotated)")
                        cols = st.columns(min(4, len(preview_frames_b64)))
                        for i, b64_img in enumerate(preview_frames_b64):
                            try:
                                img_bytes = base64.b64decode(b64_img)
                                cols[i % 4].image(img_bytes, use_column_width=True)
                            except Exception:
                                cols[i % 4].warning("Could not decode preview image.")
                    else:
                        st.info("No preview frames returned from backend.")

                    # ------------------------------
                    # Vehicle lists (no pandas!)
                    # ------------------------------
                    st.subheader("Vehicle Details")

                    def show_vehicle_list(key: str, title: str):
                        rows = result.get(key, [])
                        st.markdown(f"### {title} ({len(rows)})")
                        if not rows:
                            st.write("None.")
                            return rows

                        # Show as bullet list to avoid pandas
                        for r in rows:
                            tid = r.get("track_id", "?")
                            cls_name = r.get("class", "?")
                            speed = r.get("max_speed_kmh", 0)
                            status = r.get("status", "")
                            plate = r.get("plate_text") or "UNKNOWN"
                            st.write(
                                f"- **Track {tid}** | Class: `{cls_name}` | "
                                f"Max speed: **{speed:.1f} km/h** | "
                                f"Status: `{status}` | Plate: `{plate}`"
                            )
                        return rows

                    col_a, col_b = st.columns(2)
                    with col_a:
                        within_rows = show_vehicle_list(
                            "within_limit_vehicles", "Within Limit Vehicles"
                        )
                        grace_rows = show_vehicle_list(
                            "grace_vehicles", "Grace Vehicles"
                        )
                    with col_b:
                        over_rows = show_vehicle_list(
                            "overspeed_vehicles", "Overspeed Vehicles"
                        )

                    # ------------------------------
                    # Speed dashboard (basic stats)
                    # ------------------------------
                    st.subheader("Speed Dashboard")

                    speeds = result.get("all_speeds_kmh", [])
                    if speeds:
                        try:
                            mn = min(speeds)
                            mx = max(speeds)
                            avg = sum(speeds) / len(speeds)
                            st.write(
                                f"- Min speed: **{mn:.1f} km/h**  \n"
                                f"- Avg speed: **{avg:.1f} km/h**  \n"
                                f"- Max speed: **{mx:.1f} km/h**"
                            )
                        except Exception as e:
                            st.warning(f"Could not compute speed stats: {e}")
                    else:
                        st.info("No speed data available.")





