import streamlit as st
import tempfile
import pandas as pd
from backend.main import analyze_video_file


st.set_page_config(
    page_title="AI Speed Camera",
    layout="wide",
)

st.title("AI-Based Vehicle Speed Monitoring System")
st.write(
    "Upload a road traffic video and this app will detect vehicles, "
    "estimate their speeds using computer vision, and flag overspeeding events."
)

# Sidebar controls
with st.sidebar:
    st.header("Speed Settings")
    speed_limit = st.number_input("Speed limit (km/h)", 0.0, 200.0, 60.0, step=5.0)
    grace_kmh = st.number_input("Grace above limit (km/h)", 0.0, 50.0, 5.0, step=1.0)

    st.markdown("---")
    st.write("After upload, click **Run Analysis** to process the video.")


uploaded_video = st.file_uploader(
    "Upload traffic video (.mp4, .mov, .avi)",
    type=["mp4", "mov", "avi"],
)

run_clicked = st.button("Run Analysis", disabled=uploaded_video is None)

if uploaded_video is None:
    st.info("Please upload a video to begin.")
else:
    st.video(uploaded_video)

if uploaded_video is not None and run_clicked:
    # Save the uploaded video to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(uploaded_video.getbuffer())
        temp_video_path = tmp.name

    with st.spinner("Analyzing video, this may take a few minutes..."):
        try:
            results = analyze_video_file(
                video_path=temp_video_path,
                speed_limit_kmh=speed_limit,
                grace_kmh=grace_kmh,
            )
        except Exception as e:
            st.error(f"Error during analysis: {e}")
            st.stop()

    summary = results.get("summary_stats", {})
    overspeed_events = results.get("overspeed_events", [])
    within_limit = results.get("within_limit", [])

    # Layout for results
    st.subheader("Summary Statistics")
    if summary:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total vehicles", summary.get("num_vehicles", 0))
        col2.metric("Overspeeding", summary.get("num_overspeed", 0))
        col3.metric("Within limit", summary.get("num_within_limit", 0))

        st.write(
            f"Configured speed limit: **{summary.get('speed_limit_kmh', speed_limit)} km/h** "
            f"with **{summary.get('grace_kmh', grace_kmh)} km/h** grace."
        )
    else:
        st.write("No summary statistics available.")

    st.markdown("---")

    # Overspeed table
    st.subheader("Overspeeding Vehicles")
    if overspeed_events:
        df_over = pd.DataFrame(overspeed_events)
        st.dataframe(df_over, use_container_width=True)
    else:
        st.write("No overspeed events detected.")

    # Within-limit table
    st.subheader("Within-Limit Vehicles")
    if within_limit:
        df_within = pd.DataFrame(within_limit)
        st.dataframe(df_within, use_container_width=True)
    else:
        st.write("No vehicles within limit or insufficient tracking data.")
