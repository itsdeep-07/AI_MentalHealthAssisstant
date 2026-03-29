import streamlit as st
from streamlit_autorefresh import st_autorefresh
import json
import os
import pandas as pd
from db import (
    init_db, create_user, get_all_users, get_user,
    start_session, end_session, save_reading,
    log_stress_event, log_intervention, save_feedback,
    get_baseline, get_recent_readings, compute_and_update_baseline
)
from stress_engine import calculate_stress, get_stress_level, get_trigger_type

st.set_page_config(page_title="Mental Health Assistant", layout="wide")

script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(script_dir, "data.json")

init_db()

# ── Session state defaults ────────────────────────────────────────────────────
for key, val in {
    "user_id": None,
    "session_id": None,
    "last_event_id": None,
    "last_intervention_id": None,
    "intervention_pending_feedback": False,
    "cooldown_counter": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── User login / creation screen ──────────────────────────────────────────────
if st.session_state.user_id is None:
    st.title("Mental Health Assistant")
    st.subheader("Who are you?")

    users = get_all_users()
    if users:
        names = [u["name"] for u in users]
        choice = st.selectbox("Select your profile", ["-- Create new --"] + names)
        if choice != "-- Create new --":
            if st.button("Continue"):
                selected = next(u for u in users if u["name"] == choice)
                st.session_state.user_id = selected["user_id"]
                st.session_state.session_id = start_session(selected["user_id"])
                st.rerun()

    with st.expander("Create a new profile"):
        new_name = st.text_input("Your name")
        if st.button("Create profile") and new_name.strip():
            uid = create_user(new_name.strip())
            st.session_state.user_id = uid
            st.session_state.session_id = start_session(uid)
            st.rerun()
    st.stop()

# ── Load current data ─────────────────────────────────────────────────────────
def get_sensor_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral", "stress_level_score": 0}

st_autorefresh(interval=2000, limit=None, key="data_refresh")

user = get_user(st.session_state.user_id)
baseline = get_baseline(st.session_state.user_id)
data = get_sensor_data()
stress_score = calculate_stress(data, baseline)
stress_level = get_stress_level(stress_score)

# ── Save reading to DB every refresh ─────────────────────────────────────────
save_reading(
    st.session_state.session_id,
    data.get("current_wpm", 0),
    data.get("backspace_count", 0),
    data.get("current_emotion", "neutral"),
    stress_score
)

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_user = st.columns([4, 1])
with col_title:
    st.title("Mental Health Assistant")
with col_user:
    st.markdown(f"**{user['name']}**")
    if st.button("End session"):
        compute_and_update_baseline(st.session_state.user_id, st.session_state.session_id)
        end_session(st.session_state.session_id)
        st.session_state.user_id = None
        st.session_state.session_id = None
        st.rerun()

st.divider()

# ── Metrics row ───────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Typing speed", f"{data.get('current_wpm', 0)} WPM",
              delta=f"Baseline: {baseline['avg_wpm']:.0f}" if baseline and baseline['avg_wpm'] else None)
with c2:
    st.metric("Backspaces", f"{data.get('backspace_count', 0)}",
              delta=f"Baseline: {baseline['avg_backspace_rate']:.1f}" if baseline and baseline['avg_backspace_rate'] else None)
with c3:
    st.metric("Detected emotion", data.get("current_emotion", "Neutral"))
with c4:
    st.metric("Stress score", f"{stress_score}/100")

# ── Stress bar ────────────────────────────────────────────────────────────────
st.subheader("Real-time stress level")
level_labels = {"relaxed": "Relaxed", "mild": "Mild", "moderate": "Moderate", "high": "High"}
level_colors = {"relaxed": "success", "mild": "warning", "moderate": "warning", "high": "error"}

getattr(st, level_colors[stress_level])(
    f"Status: **{level_labels[stress_level]}** — Score {stress_score}/100"
)
st.progress(stress_score / 100.0)

# ── Stress history chart ──────────────────────────────────────────────────────
recent = get_recent_readings(st.session_state.session_id, limit=60)
if len(recent) > 1:
    df = pd.DataFrame(recent[::-1])
    st.subheader("Stress trend this session")
    st.line_chart(df.set_index("timestamp")["stress_score"])

# ── Intervention ──────────────────────────────────────────────────────────────
if stress_score >= 70:
    st.session_state.cooldown_counter = 0

    if not st.session_state.intervention_pending_feedback:
        trigger = get_trigger_type(data, baseline)
        event_id = log_stress_event(st.session_state.session_id, stress_score, trigger)
        st.session_state.last_event_id = event_id

    st.markdown("### Elevated stress detected")
    st.write("Based on your typing patterns and facial expression, here is a short exercise.")

    tab1, tab2, tab3 = st.tabs(["Box breathing", "Posture check", "Screen break"])

    with tab1:
        st.info("Inhale 4s → Hold 4s → Exhale 4s → Hold 4s. Repeat 3 times.")
        st.image("https://media.giphy.com/media/8Y7mSvoZJdYQ0/giphy.gif", width=280)
        if st.button("I completed the breathing exercise"):
            iid = log_intervention(st.session_state.last_event_id, "breathing", "4-4-4 box breathing")
            st.session_state.last_intervention_id = iid
            st.session_state.intervention_pending_feedback = True
            st.rerun()

    with tab2:
        st.info("Sit up straight. Drop your shoulders. Look 20 feet away for 20 seconds.")
        if st.button("Done with posture check"):
            iid = log_intervention(st.session_state.last_event_id, "posture", "20-20-20 posture rule")
            st.session_state.last_intervention_id = iid
            st.session_state.intervention_pending_feedback = True
            st.rerun()

    with tab3:
        st.info("Step away from the screen for 5 minutes. Stretch your wrists and neck.")
        if st.button("Back from break"):
            iid = log_intervention(st.session_state.last_event_id, "break", "5 min screen break")
            st.session_state.last_intervention_id = iid
            st.session_state.intervention_pending_feedback = True
            st.rerun()

# ── Feedback collection ───────────────────────────────────────────────────────
if st.session_state.intervention_pending_feedback:
    st.markdown("### Was that helpful?")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Yes, it helped"):
            save_feedback(st.session_state.last_intervention_id, True)
            st.session_state.intervention_pending_feedback = False
            st.success("Glad it helped! Back to monitoring.")
            st.rerun()
    with col_no:
        if st.button("Not really"):
            save_feedback(st.session_state.last_intervention_id, False)
            st.session_state.intervention_pending_feedback = False
            st.rerun()