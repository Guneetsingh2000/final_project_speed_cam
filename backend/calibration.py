calib_store = {}

def compute_mpp(p1, p2, lane_width_m):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = (dx*dx + dy*dy)**0.5
    return lane_width_m / dist

def save_calibration(video_id, mpp, fps):
    calib_store[video_id] = {"mpp": mpp, "fps": fps}

def load_calibration(video_id):
    return calib_store[video_id]["mpp"], calib_store[video_id]["fps"]

