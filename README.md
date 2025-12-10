# final_project_speed_cam
# 🚗 AI-Powered Vehicle Speed Detection System  
### Deep Learning • Object Detection • Object Tracking • Speed Estimation • Streamlit + FastAPI

This project is an end-to-end computer vision pipeline that detects vehicles in traffic videos, tracks them across frames, and estimates their speed based on pixel movement. The system flags overspeeding vehicles and displays results through a Streamlit web UI connected to a FastAPI backend. It was developed individually as part of the final project for Advanced Neural Networks & Deploying AI Systems.

---

## 📌 Key Features
- **YOLOv8n** for fast vehicle detection  
- **Centroid-based tracking** for consistent object IDs  
- **Speed estimation** using pixel displacement, FPS, and calibration  
- **Overspeed detection** with configurable limit & grace  
- **Streamlit UI** for uploading videos and viewing results  
- **FastAPI backend** for processing and returning annotated output  
- **Cloud-ready deployment** (Streamlit Cloud / AWS EC2 / Render)  
- Clean, modular MLOps-style structure

---

## 🧠 How Speed Calculation Works

The backend processes the video in several steps:

### 1. Detection  
Each frame is passed through YOLOv8n to identify vehicles (car, truck, bus, etc.).

### 2. Tracking  
A simple centroid-tracking method assigns a **unique ID** to each vehicle by comparing movement across consecutive frames.

### 3. Measuring Distance  
For each tracked ID:

