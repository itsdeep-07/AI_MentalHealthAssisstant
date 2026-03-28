import time
import json
import threading
import os
from pynput import keyboard

# Define data.json path relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(script_dir, "..", "data.json")

WPM_WINDOW = 60 # seconds to average WPM
UPDATE_INTERVAL = 2 # seconds to write to json

class KeyboardTracker:
    def __init__(self):
        self.key_presses = 0
        self.backspaces = 0
        self.start_time = time.time()
        self.last_type_time = time.time()
        self.running = True

    def on_press(self, key):
        self.key_presses += 1
        self.last_type_time = time.time()
        if key == keyboard.Key.backspace:
            self.backspaces += 1

    def update_json(self):
        while self.running:
            time.sleep(UPDATE_INTERVAL)
            current_time = time.time()
            elapsed = current_time - self.start_time
            
            if current_time - self.last_type_time > 3.0:
                # If nothing typed in 3 seconds, stop WPM counter
                wpm = 0
                # Reset window so it recalculates freshly when they resume
                self.key_presses = 0
                self.start_time = current_time
            else:
                # Avoid divide by zero
                if elapsed < 1:
                    continue
                # Approximating 5 characters per word
                wpm = int((self.key_presses / 5) / (elapsed / 60))
            
            try:
                # Read existing data to not overwrite other sensors
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                
                data["current_wpm"] = wpm
                data["backspace_count"] = self.backspaces
                
                # Write updated data back
                with open(DATA_FILE, "w") as f:
                    json.dump(data, f)
            except Exception as e:
                print(f"Error updating JSON: {e}")

            # Reset window periodically
            if elapsed > WPM_WINDOW:
                self.key_presses = 0
                self.backspaces = 0
                self.start_time = time.time()

    def start(self):
        print("Staring Keyboard Tracker. Press Ctrl+C to stop.")
        
        # Ensure initial JSON setup in case it's missing
        if not os.path.exists(DATA_FILE):
             with open(DATA_FILE, "w") as f:
                 json.dump({"current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral", "stress_level_score": 0}, f)

        # Start JSON updater thread
        updater_thread = threading.Thread(target=self.update_json, daemon=True)
        updater_thread.start()

        # Start listening to keyboard events (blocks main thread)
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()

if __name__ == "__main__":
    tracker = KeyboardTracker()
    tracker.start()
