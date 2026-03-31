import json
import os
import time
import statistics
from pynput import keyboard

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(script_dir, "data.json")

WINDOW = 10
key_times = []
last_key_time = 0

backspace_count = 0
total_keypresses = 0
consecutive_backspaces = 0
frustration_deletes = 0
pause_count = 0
intervals = []

last_reset_time = time.time()

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

def write_data(wpm, backspaces, total_keys, typo_rate, frustration, rhythm, pauses):
    current = read_data()
    current["current_wpm"] = wpm
    current["backspace_count"] = backspaces
    current["total_keypresses"] = total_keys
    current["typo_rate"] = typo_rate
    current["frustration_deletes"] = frustration
    current["rhythm_variability"] = rhythm
    current["pause_count"] = pauses
    with open(DATA_FILE, "w") as f:
        json.dump(current, f)

def on_press(key):
    global backspace_count, total_keypresses, consecutive_backspaces, frustration_deletes
    global pause_count, intervals, last_key_time, last_reset_time

    now = time.time()
    total_keypresses += 1
    key_times.append(now)

    if last_key_time > 0:
        gap = now - last_key_time
        intervals.append(gap)
        if len(intervals) > 50:
            intervals.pop(0)
        if gap > 3.0:
            pause_count += 1
    last_key_time = now

    cutoff = now - WINDOW
    while key_times and key_times[0] < cutoff:
        key_times.pop(0)

    if key == keyboard.Key.backspace:
        backspace_count += 1
        consecutive_backspaces += 1
        if consecutive_backspaces == 5:
            frustration_deletes += 1
    else:
        consecutive_backspaces = 0

    chars_per_sec = len(key_times) / WINDOW
    wpm = int((chars_per_sec / 5) * 60)

    typo_rate = backspace_count / total_keypresses if total_keypresses > 0 else 0.0
    
    rhythm_variability = 0.0
    if len(intervals) > 1:
        rhythm_variability = statistics.stdev(intervals)

    write_data(wpm, backspace_count, total_keypresses, typo_rate, frustration_deletes, rhythm_variability, pause_count)

    if now - last_reset_time >= 90:
        backspace_count = 0
        total_keypresses = 0
        frustration_deletes = 0
        pause_count = 0
        consecutive_backspaces = 0
        last_reset_time = now

def start():
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    print("Keyboard tracker running...")
    start()
