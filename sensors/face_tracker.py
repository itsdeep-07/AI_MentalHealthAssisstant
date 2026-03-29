import json
import os
import time
import cv2
from deepface import DeepFace

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(script_dir, "data.json")

def read_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral", "stress_level_score": 0}

def write_emotion(emotion):
    current = read_data()
    current["current_emotion"] = emotion
    with open(DATA_FILE, "w") as f:
        json.dump(current, f)

def start():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera not available. Face tracker exiting.")
        write_emotion("Neutral")
        return

    print("Face tracker running...")
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue
        try:
            result = DeepFace.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False,
                silent=True
            )
            emotion = result[0]["dominant_emotion"].capitalize()
        except Exception as e:
            print(f"DeepFace Exception: {e}")
            emotion = "Neutral"

        write_emotion(emotion)
        time.sleep(2)

    cap.release()

if __name__ == "__main__":
    start()