import json
import os
import time
from pynput import keyboard

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(script_dir, "data.json")

WINDOW = 10
key_times = []
backspace_count = 0

def read_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral", "stress_level_score": 0}

def write_data(wpm, backspaces):
    current = read_data()
    current["current_wpm"] = wpm
    current["backspace_count"] = backspaces
    with open(DATA_FILE, "w") as f:
        json.dump(current, f)

def on_press(key):
    global backspace_count
    now = time.time()
    key_times.append(now)

    cutoff = now - WINDOW
    while key_times and key_times[0] < cutoff:
        key_times.pop(0)

    if key == keyboard.Key.backspace:
        backspace_count += 1

    chars_per_sec = len(key_times) / WINDOW
    wpm = int((chars_per_sec / 5) * 60)

    write_data(wpm, backspace_count)

    # Reset backspace count every 30s
    if int(now) % 30 == 0:
        backspace_count = 0

def start():
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    print("Keyboard tracker running...")
    start()