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
    return {
        "current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral", "stress_level_score": 0,
        "total_keypresses": 0, "typo_rate": 0.0, "frustration_deletes": 0, "rhythm_variability": 0.0,
        "pause_count": 0, "emotion_duration_seconds": 0
    }

def write_emotion(emotion, duration):
    current = read_data()
    current["current_emotion"] = emotion
    current["emotion_duration_seconds"] = duration
    with open(DATA_FILE, "w") as f:
        json.dump(current, f)

def start():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera not available. Face tracker exiting.")
        write_emotion("Neutral", 0)
        return

    print("Face tracker running...")
    previous_emotion = None
    emotion_start_time = None

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
            res = result[0] if isinstance(result, list) else result
            emotions = res.get("emotion", {})
            
            # Demo Mode: Highly sensitive thresholds for stress/anxiety
            negative_score = emotions.get("sad", 0) + emotions.get("angry", 0) + emotions.get("fear", 0) + emotions.get("disgust", 0)
            
            if negative_score > 25:
                emotion = "Anxious"
            elif negative_score > 8:
                emotion = "Stress"
            elif emotions.get("happy", 0) > 10:
                emotion = "Happy"
            else:
                emotion = res.get("dominant_emotion", "Neutral").capitalize()
                
        except Exception as e:
            emotion = "Neutral"

        now = time.time()
        if emotion == previous_emotion:
            duration = int(now - emotion_start_time) if emotion_start_time else 0
        else:
            emotion_start_time = now
            duration = 0
            previous_emotion = emotion

        write_emotion(emotion, duration)
        time.sleep(2)

    cap.release()

if __name__ == "__main__":
    start()
