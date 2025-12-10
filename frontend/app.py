# frontend/app.py

import os
import io
import requests
import streamlit as st
import pandas as pd

# === Backend URL ===
# Locally: will default to http://127.0.0.1:8000
# On Streamlit Cloud: set BACKEND_URL in the app settings to your EC2 URL.
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="YOLO Speed Camera – Final Project",
    layout="wide",
)

st.title("YOLO-based License Plate Speed Camera")
st.write(
    "Upload a traffic video and the system will detect vehicles, estimate their speed, "
    "and flag overspeeding events."
)

# --- Sidebar info ---
st.sidebar.header("Backend Status")
try:
    health_resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if health_resp.ok:
        st.sidebar.success("Backend: Online")
    else:
        st.sidebar.warning("Backend reachable but unhealthy")
except Exception:
    st.sidebar.error("Backend: Not reachable")
st.sidebar.write(f"Backend URL: `{BACKEND_URL}`")

st.sidebar.markdown("---")
st.sidebar.subheader("Speed Settings")
speed_limit = st.sidebar.number_input("Speed limit (km/h)", min_value=10, max_value=200, value=60)
grace = st.sidebar.number_input("Grace over limit (km/h)", min_value=0, max_value=50, value=5)

st.sidebar.markdown(
    "These values are mainly for display in the report / tables. "
    "The actual limit used by the backend may come from calibration or config."
)

# --- Main upload area ---
uploaded_file = st.file_uploader("Upload a traffic video (.mp4)", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    st.video(uploaded_file)

    if st.button("Analyze Video"):
        with st.spinner("Uploading video and waiting for analysis..."):
            # Send video to backend
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
            try:
                resp = requests.post(f"{BACKEND_URL}/analyze_video", files=files, timeout=600)
            except Exception as e:
                st.error(f"Error contacting backend: {e}")
                st.stop()

        if not resp.ok:
            st.error(f"Backend returned error {resp.status_code}: {resp.text}")
            st.stop()

        payload = resp.json()
        if payload.get("status") != "ok":
            st.error(f"Backend error: {payload}")
            st.stop()

        data = payload.get("data", {})

        # Expected structure (you can adapt to match what your backend returns):
        # data = {
        #   "summary": {
        #       "total_vehicles": int,
        #       "overspeed_count": int,
        #       "within_limit_count": int,
        #       "avg_speed": float,
        #   },
        #   "overspeed_events": [ {...}, ... ],
        #   "within_limit": [ {...}, ... ],
        # }

        st.success("Analysis completed!")

        # --- Summary section ---
        st.subheader("Summary Statistics")
        summary = data.get("summary", {})
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Vehicles", summary.get("total_vehicles", 0))
        col2.metric("Overspeeding Vehicles", summary.get("overspeed_count", 0))
        col3.metric("Within Limit", summary.get("within_limit_count", 0))
        col4.metric("Average Speed (km/h)", round(summary.get("avg_speed", 0.0), 2))

        st.markdown(
            f"**Configured Speed Limit:** {speed_limit} km/h (+{grace} km/h grace)  "
        )

        # --- Overspeed table ---
        st.subheader("Overspeeding Vehicles")
        overspeed_events = data.get("overspeed_events", [])

        def normalize_rows(rows):
            """Make sure we can show dicts or simple lists."""
            if isinstance(rows, list) and len(rows) > 0:
                if isinstance(rows[0], dict):
                    return pd.DataFrame(rows)
                else:
                    # assume [track_id, class_id, max_speed, ...]
                    return pd.DataFrame(
                        rows,
                        columns=[
                            "track_id",
                            "class_id",
                            "max_speed_kmh",
                            "limit_kmh",
                            "plate",
                        ][: len(rows[0])],
                    )
            return pd.DataFrame()

        df_over = normalize_rows(overspeed_events)
        if not df_over.empty:
            st.dataframe(df_over, use_container_width=True)
        else:
            st.info("No overspeeding vehicles detected in this clip.")

        # --- Within-limit table ---
        st.subheader("Within Limit Vehicles")
        within = data.get("within_limit", [])
        df_within = normalize_rows(within)
        if not df_within.empty:
            st.dataframe(df_within, use_container_width=True)
        else:
            st.info("No within-limit vehicles recorded or not returned by backend.")

        # Optional: download CSVs
        st.markdown("### Export Results")
        col_a, col_b = st.columns(2)
        if not df_over.empty:
            csv_over = df_over.to_csv(index=False).encode("utf-8")
            col_a.download_button(
                "Download Overspeed CSV",
                data=csv_over,
                file_name="overspeed_vehicles.csv",
                mime="text/csv",
            )
        if not df_within.empty:
            csv_within = df_within.to_csv(index=False).encode("utf-8")
            col_b.download_button(
                "Download Within-Limit CSV",
                data=csv_within,
                file_name="within_limit_vehicles.csv",
                mime="text/csv",
            )

else:
    st.info("Upload a video to begin analysis.")


