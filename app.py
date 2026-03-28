import streamlit as st
from streamlit_autorefresh import st_autorefresh
import json
import os

st.set_page_config(page_title="Context-Aware Mental Health Assistant", layout="wide")

# Path to data
script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(script_dir, "data.json")

# Auto-refresh UI every 2 seconds
st_autorefresh(interval=2000, limit=None, key="data_refresh")

def get_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral", "stress_level_score": 0}

def calculate_stress(data):
    wpm = data.get("current_wpm", 0)
    backspaces = data.get("backspace_count", 0)
    emotion = data.get("current_emotion", "Neutral").lower()
    
    score = 0
    
    # Emotion heuristics
    if emotion in ["angry", "sad", "fear", "disgust"]:
        score += 50
    elif emotion == "neutral":
        score += 10
    
    # Typing heuristics
    if wpm > 70:
        score += 20 # Typing very fast (potential stress)
    if backspaces > 10:
        score += 30 # Making lots of errors
        
    # Cap at 100
    score = min(100, score)
    return score

data = get_data()
stress_score = calculate_stress(data)

st.title("🧠 Context-Aware Mental Health Assistant")
st.markdown("Monitoring subtle behavioral signals in the background without interrupting your workflow...")

# Metrics Layout
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Typing Speed", f"{data.get('current_wpm', 0)} WPM")
    
with col2:
    st.metric("Error Rate (Backspaces)", f"{data.get('backspace_count', 0)}")
    
with col3:
    st.metric("Current Computed Emotion", data.get('current_emotion', 'Neutral'))
    
st.divider()

# Stress Level indicator
st.subheader("Real-Time Stress Level")

# Dynamic color for progress bar
if stress_score < 40:
    st.success(f"**Stress Score: {stress_score}/100** (Relaxed)")
elif stress_score < 70:
    st.warning(f"**Stress Score: {stress_score}/100** (Moderate)")
else:
    st.error(f"**Stress Score: {stress_score}/100** (High)")

st.progress(stress_score / 100.0)

# Interventions
if stress_score >= 70:
    st.markdown("### 🛑 Elevated Stress Detected")
    st.write("Based on your recent typing patterns and facial expressions, we recommend a short break.")
    
    tab1, tab2 = st.tabs(["Box Breathing", "Posture Check"])
    
    with tab1:
        st.info("Inhale for 4 seconds, hold for 4 seconds, exhale for 4 seconds, hold for 4 seconds.")
        # Render a simple animated breathing element
        st.markdown("![Breathe](https://media.giphy.com/media/8Y7mSvoZJdYQ0/giphy.gif)")
    
    with tab2:
        st.info("Please sit up straight, drop your shoulders, and look 20 feet away for 20 seconds.")
