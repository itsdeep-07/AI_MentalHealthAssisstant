import streamlit as st
from datetime import datetime, timedelta
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
    "session_start_time": None,
    "break_due_at": None,
    "break_active": False,
    "break_start": None,
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
                st.session_state.session_start_time = datetime.now()
                st.session_state.break_due_at = datetime.now() + timedelta(minutes=20)
                st.rerun()

    with st.expander("Create a new profile"):
        new_name = st.text_input("Your name")
        if st.button("Create profile") and new_name.strip():
            uid = create_user(new_name.strip())
            st.session_state.user_id = uid
            st.session_state.session_id = start_session(uid)
            st.session_state.session_start_time = datetime.now()
            st.session_state.break_due_at = datetime.now() + timedelta(minutes=20)
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
session_minutes = 0
if st.session_state.session_start_time:
    session_minutes = (datetime.now() - st.session_state.session_start_time).seconds / 60
stress_score = calculate_stress(data, baseline, session_minutes)
stress_level = get_stress_level(stress_score)

# ── Save reading to DB every refresh ─────────────────────────────────────────
save_reading(
    st.session_state.session_id,
    data.get("current_wpm", 0),
    data.get("backspace_count", 0),
    data.get("current_emotion", "neutral"),
    stress_score,
    data.get("typo_rate", 0.0),
    data.get("frustration_deletes", 0),
    data.get("rhythm_variability", 0.0),
    data.get("pause_count", 0),
    data.get("emotion_duration_seconds", 0)
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

# ── 20-20-20 Eye Break System ─────────────────────────────────────────────────
if st.session_state.break_due_at and datetime.now() >= st.session_state.break_due_at:
    if not st.session_state.break_active:
        st.session_state.break_active = True
        st.session_state.break_start = datetime.now()

if st.session_state.break_active:
    st.markdown('<div style="background-color:rgba(0,128,128,0.1); padding:20px; border-radius:10px; border:1px solid teal; text-align:center; margin-bottom: 20px;">'
                '<h3 style="color:teal; margin-top:0;">👁️ Time for a 20-20-20 break</h3>'
                '<p>Look at something 20 feet away to reduce eye strain and mental fatigue.</p>'
                '</div>', unsafe_allow_html=True)
                
    elapsed = (datetime.now() - st.session_state.break_start).seconds
    remaining = max(0, 20 - elapsed)
    
    st.progress(min(1.0, elapsed / 20.0))
    st.caption(f"Waiting for {remaining} seconds...")
    
    if remaining <= 0:
        st.session_state.break_active = False
        st.session_state.break_due_at = datetime.now() + timedelta(minutes=20)
        st.rerun()


# ── Metrics row ───────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c4, c5, c6 = st.columns(3)

with c1:
    delta_wpm = None
    if baseline and baseline.get('avg_wpm', 0) > 0:
        diff_pct = (data.get('current_wpm', 0) / baseline['avg_wpm']) * 100 - 100
        delta_wpm = f"+{diff_pct:.0f}% above baseline" if diff_pct > 0 else "Normal"
    st.metric("Typing speed", f"{data.get('current_wpm', 0)} WPM", delta=delta_wpm, delta_color="inverse" if delta_wpm != "Normal" else "normal")
with c2:
    delta_bs = None
    if baseline and baseline.get('avg_backspace_rate', 0) > 0:
        diff_pct = (data.get('backspace_count', 0) / (baseline['avg_backspace_rate']+0.1)) * 100 - 100
        delta_bs = f"+{diff_pct:.0f}% above baseline" if diff_pct > 0 else "Normal"
    st.metric("Backspaces", f"{data.get('backspace_count', 0)}", delta=delta_bs, delta_color="inverse" if delta_bs != "Normal" else "normal")
with c3:
    st.metric("Detected emotion", data.get("current_emotion", "Neutral"))
with c4:
    typo_pct = data.get("typo_rate", 0.0) * 100
    st.metric("Typo rate", f"{typo_pct:.1f}%")
with c5:
    st.metric("Session time", f"{int(session_minutes)} min")
with c6:
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
    trigger_labels = {
        "high_wpm": "Typing faster than usual",
        "high_typo_rate": "High error rate in typing",
        "frustration_deletes": "Repeated aggressive deletions detected",
        "erratic_rhythm": "Irregular typing rhythm",
        "frequent_pauses": "Frequent mid-session pauses",
        "negative_emotion": "Sustained negative facial expression",
        "typing_speed": "Typing faster than usual",
        "typing_errors": "High error rate",
        "facial_expression": "Sustained negative emotion"
    }
    trigger_list = [t.strip() for t in trigger.split(",") if t.strip()]
    if trigger_list and trigger_list[0] != "unknown":
        with st.expander("Why was this triggered?"):
            for t in trigger_list:
                label = trigger_labels.get(t, t)
                st.markdown(f"• {label}")

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