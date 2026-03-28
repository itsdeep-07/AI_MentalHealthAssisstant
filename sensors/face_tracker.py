import cv2
import json
import time
import os
import threading
from deepface import DeepFace

# Define data.json path relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(script_dir, "..", "data.json")

# How often to run deepface analysis (seconds)
ANALYZE_INTERVAL = 3  

class FaceTracker:
    def __init__(self):
        self.running = True
        self.cap = cv2.VideoCapture(0)
        self.latest_frame = None

    def capture_frames(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.latest_frame = frame
            time.sleep(0.05)
            
    def analyze_emotion(self):
        while self.running:
            time.sleep(ANALYZE_INTERVAL)
            if self.latest_frame is None:
                continue
                
            try:
                # DeepFace analyze the frame directly from memory
                result = DeepFace.analyze(
                    self.latest_frame, 
                    actions=['emotion'], 
                    enforce_detection=False,
                    silent=True
                )
                
                dominant_emotion = result[0]['dominant_emotion']
                
                # Update JSON
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    
                data["current_emotion"] = dominant_emotion.capitalize()
                
                with open(DATA_FILE, "w") as f:
                    json.dump(data, f)
                    
            except Exception as e:
                print(f"Error analyzing face: {e}")

    def start(self):
        print("Starting Face Tracker. Press Ctrl+C to stop.")
        
        # Start capture thread
        capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        capture_thread.start()
        
        # Start analyze thread
        analyze_thread = threading.Thread(target=self.analyze_emotion, daemon=True)
        analyze_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            self.cap.release()
            print("Face tracker stopped.")

if __name__ == "__main__":
    tracker = FaceTracker()
    tracker.start()
