# hardware/capture_video.py

import cv2
import time

def main():
    # 0 = default USB camera. For Pi camera, this might be 0 or 1 depending on setup.
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Could not open camera. Check connection / index.")
        return

    # Read one frame to get resolution
    ret, frame = cap.read()
    if not ret:
        print("❌ Could not read frame from camera.")
        cap.release()
        return

    height, width = frame.shape[:2]

    # Define output video
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter("edge_clip.mp4", fourcc, 30.0, (width, height))

    print("🎥 Recording started. Press 'q' to stop or wait 15 seconds...")

    start = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame.")
            break

        out.write(frame)
        cv2.imshow("Recording - press q to stop", frame)

        # Stop after ~15 seconds OR if user presses 'q'
        if (time.time() - start) > 15:
            print("⏱ 15 seconds reached, stopping.")
            break

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("🛑 'q' pressed, stopping.")
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("✅ Saved video as edge_clip.mp4 in this folder.")

if __name__ == "__main__":
    main()
