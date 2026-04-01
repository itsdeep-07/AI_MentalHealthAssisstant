import streamlit as st
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
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

st.set_page_config(page_title="MindTrack", layout="wide", initial_sidebar_state="collapsed")

# Hide default Streamlit chrome
st.markdown("""
<style>
#MainMenu, header, footer { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

script_dir = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(script_dir, "data.json")
init_db()

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
    "pending_action": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_sensor_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_wpm": 0, "backspace_count": 0, "current_emotion": "Neutral",
        "stress_level_score": 0, "typo_rate": 0.0, "frustration_deletes": 0,
        "rhythm_variability": 0.0, "pause_count": 0, "emotion_duration_seconds": 0
    }

def trigger_label(t):
    return {
        "high_wpm": "Typing faster than usual",
        "high_typo_rate": "High error rate in typing",
        "frustration_deletes": "Repeated aggressive deletions",
        "erratic_rhythm": "Irregular typing rhythm",
        "frequent_pauses": "Frequent mid-session pauses",
        "negative_emotion": "Sustained negative facial expression",
    }.get(t, t)

def emotion_emoji(emotion):
    return {
        "happy": "😊", "sad": "😟", "angry": "😠", "fear": "😨",
        "disgust": "🤢", "surprise": "😮", "neutral": "😐",
    }.get(emotion.lower(), "😐")

# ── Login screen ──────────────────────────────────────────────────────────────
if st.session_state.user_id is None:
    login_html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Outfit', sans-serif;
  background: radial-gradient(circle at top right, #311847, #0f172a 50%), radial-gradient(circle at bottom left, #064e3b, #0f172a 50%);
  background-color: #0f172a;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 3.5rem 2.5rem;
  width: 400px;
  text-align: center;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.6);
}
.logo {
  width: 56px; height: 56px;
  background: linear-gradient(135deg, #8b5cf6, #06b6d4);
  border-radius: 16px;
  margin: 0 auto 1.5rem;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 10px 25px rgba(139,92,246,0.3);
}
.logo svg { width: 28px; height: 28px; fill: none; stroke: #fff; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
h1 { font-size: 28px; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em; }
.sub { font-size: 15px; color: #94a3b8; margin-top: 8px; margin-bottom: 2rem; }
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <svg viewBox="0 0 24 24"><path d="M12 2C8 2 5 5 5 9c0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>
  </div>
  <h1>MindTrack</h1>
  <p class="sub">Context-Aware Mental Health Assistant</p>
</div>
</body>
</html>
"""
    components.html(login_html, height=360)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center; color: #f8fafc; font-family: sans-serif;'>Authentication</h3>", unsafe_allow_html=True)
        users = get_all_users()
        if users:
            names = [u["name"] for u in users]
            choice = st.selectbox("Select your profile", ["— Create new profile —"] + names, label_visibility="collapsed")
            if choice != "— Create new profile —":
                if st.button("Continue →", type="primary", use_container_width=True):
                    selected = next(u for u in users if u["name"] == choice)
                    st.session_state.user_id = selected["user_id"]
                    st.session_state.session_id = start_session(selected["user_id"])
                    st.session_state.session_start_time = datetime.now()
                    st.session_state.break_due_at = datetime.now() + timedelta(minutes=20)
                    st.rerun()
        
        with st.expander("Create a new profile"):
            new_name = st.text_input("Your name")
            if st.button("Create profile", use_container_width=True) and new_name.strip():
                uid = create_user(new_name.strip())
                st.session_state.user_id = uid
                st.session_state.session_id = start_session(uid)
                st.session_state.session_start_time = datetime.now()
                st.session_state.break_due_at = datetime.now() + timedelta(minutes=20)
                st.rerun()
    st.stop()

# ── Main session ──────────────────────────────────────────────────────────────
st_autorefresh(interval=2000, limit=None, key="data_refresh")

user = get_user(st.session_state.user_id)
baseline = get_baseline(st.session_state.user_id)
data = get_sensor_data()

session_minutes = 0
if st.session_state.session_start_time:
    session_minutes = (datetime.now() - st.session_state.session_start_time).seconds / 60

stress_score = calculate_stress(data, baseline, session_minutes)
stress_level = get_stress_level(stress_score)

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

# Eye-break logic
if st.session_state.break_due_at and datetime.now() >= st.session_state.break_due_at:
    if not st.session_state.break_active:
        st.session_state.break_active = True
        st.session_state.break_start = datetime.now()

break_remaining = 0
break_pct = 100
if st.session_state.break_active and st.session_state.break_start:
    elapsed = (datetime.now() - st.session_state.break_start).seconds
    break_remaining = max(0, 20 - elapsed)
    break_pct = min(100, int((elapsed / 20) * 100))
    if break_remaining <= 0:
        st.session_state.break_active = False
        st.session_state.break_due_at = datetime.now() + timedelta(minutes=20)

# Recent readings for chart
recent = get_recent_readings(st.session_state.session_id, limit=60)
chart_data = [r["stress_score"] for r in reversed(recent)] if len(recent) > 1 else [0]

# Stress level info
level_map = {
    "relaxed":  {"label": "Relaxed",  "cls": "badge-relaxed"},
    "mild":     {"label": "Mild",     "cls": "badge-mild"},
    "moderate": {"label": "Moderate", "cls": "badge-moderate"},
    "high":     {"label": "High",     "cls": "badge-high"},
}
level_info = level_map[stress_level]

# WPM delta
wpm_delta = ""
if baseline and baseline.get("avg_wpm", 0) > 0:
    diff_pct = (data.get("current_wpm", 0) / baseline["avg_wpm"]) * 100 - 100
    wpm_delta = f"+{diff_pct:.0f}% above baseline" if diff_pct > 0 else "Normal"
else:
    wpm_delta = "No baseline yet"

# Typo delta
typo_pct = data.get("typo_rate", 0.0) * 100
typo_class = "delta-up" if typo_pct > 15 else "delta-ok"
typo_delta = "High" if typo_pct > 15 else "Normal"

# Backspace delta
bs_delta = ""
if baseline and baseline.get("avg_backspace_rate", 0) > 0:
    diff_pct = (data.get("backspace_count", 0) / (baseline["avg_backspace_rate"] + 0.1)) * 100 - 100
    bs_delta = f"+{diff_pct:.0f}% above baseline" if diff_pct > 0 else "Normal"
else:
    bs_delta = "No baseline yet"

# Intervention
trigger = ""
show_intervention = stress_score >= 70
if show_intervention:
    st.session_state.cooldown_counter = 0
    if not st.session_state.intervention_pending_feedback:
        trigger = get_trigger_type(data, baseline)
        event_id = log_stress_event(st.session_state.session_id, stress_score, trigger)
        st.session_state.last_event_id = event_id

trigger_list = [t.strip() for t in trigger.split(",") if t.strip()] if trigger else []
trigger_pills_html = "".join(
    f'<span class="trigger-pill">{trigger_label(t)}</span>'
    for t in trigger_list if t != "unknown"
)

emotion_str = data.get("current_emotion", "Neutral")
emotion_em = emotion_emoji(emotion_str)
emotion_dur = data.get("emotion_duration_seconds", 0)

user_initials = "".join(w[0].upper() for w in user["name"].split()[:2])

break_banner_display = "flex" if st.session_state.break_active else "none"
intervention_display = "block" if show_intervention else "none"
chart_json = json.dumps(chart_data)

# ── Full custom HTML dashboard ────────────────────────────────────────────────
html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-main: #0f172a;
  --glass-bg: rgba(30, 41, 59, 0.45);
  --glass-border: rgba(255, 255, 255, 0.08);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --accent-cyan: #06b6d4;
  --accent-violet: #8b5cf6;
  --accent-pink: #ec4899;
  --accent-orange: #f97316;
  --accent-emerald: #10b981;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ 
  font-family: 'Outfit', sans-serif; 
  background-color: var(--bg-main);
  background-image: 
    radial-gradient(circle at 15% 50%, rgba(139, 92, 246, 0.15), transparent 40%),
    radial-gradient(circle at 85% 30%, rgba(6, 182, 212, 0.15), transparent 40%),
    radial-gradient(circle at 50% 100%, rgba(236, 72, 153, 0.1), transparent 50%);
  background-attachment: fixed;
  color: var(--text-primary); 
}}
.shell {{
  max-width: 1040px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem 4rem;
}}

/* ── Top bar ── */
.topbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2.5rem;
}}
.brand {{ display: flex; align-items: center; gap: 16px; }}
.brand-icon {{
  width: 44px; height: 44px;
  background: linear-gradient(135deg, var(--accent-violet), var(--accent-cyan));
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 24px rgba(139,92,246,0.3);
}}
.brand-icon svg {{ width: 22px; height: 22px; fill: none; stroke: #fff; stroke-width: 2.5; stroke-linecap: round; }}
.brand-name {{ font-size: 22px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }}
.brand-sub {{ font-size: 13px; color: var(--text-secondary); display: block; margin-top: 2px; }}
.user-chip {{
  display: flex; align-items: center; gap: 10px;
  padding: 6px 16px 6px 6px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: 100px;
  font-size: 14px; font-weight: 500; color: var(--text-primary);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}}
.avatar {{
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, #334155, #1e293b);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; color: var(--accent-cyan);
  border: 1px solid rgba(255,255,255,0.1);
}}

/* ── Eye break ── */
.eye-break {{
  display: {break_banner_display};
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background: linear-gradient(90deg, rgba(6, 182, 212, 0.1), rgba(16, 185, 129, 0.1));
  border: 1px solid rgba(6, 182, 212, 0.3);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 10px 30px rgba(6, 182, 212, 0.15);
}}
.eye-left {{ display: flex; align-items: center; gap: 16px; }}
.eye-title {{ font-size: 16px; font-weight: 600; color: var(--accent-cyan); text-shadow: 0 0 10px rgba(6, 182, 212, 0.4); }}
.eye-desc {{ font-size: 14px; color: #cbd5e1; margin-top: 4px; }}
.break-progress-wrap {{ flex: 1; max-width: 260px; }}
.break-bar-bg {{ height: 8px; background: rgba(0,0,0,0.3); border-radius: 8px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.5); }}
.break-bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-emerald)); border-radius: 8px; width: {break_pct}%; transition: width 1s linear; box-shadow: 0 0 12px var(--accent-cyan); }}
.break-timer {{ font-size: 13px; color: var(--text-secondary); margin-top: 8px; font-family: 'Space Mono', monospace; text-align: right; }}

/* ── Section label ── */
.section-label {{
  font-size: 13px; font-weight: 600; color: var(--text-secondary);
  letter-spacing: 0.1em; text-transform: uppercase;
  margin-bottom: 1.25rem;
  display: flex; align-items: center; gap: 8px;
}}
.section-label::after {{ content: ''; height: 1px; flex: 1; background: linear-gradient(90deg, var(--glass-border), transparent); }}

/* ── Metric cards (Glassmorphism + Neon) ── */
.metrics-grid {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 2.5rem;
}}
.metric-card {{
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-top: 2px solid var(--ac);
  border-radius: 20px;
  padding: 1.5rem;
  position: relative;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2), inset 0 20px 40px -20px var(--ac-glow);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}
.metric-card:hover {{ transform: translateY(-4px); border-color: rgba(255,255,255,0.2); }}
.metric-label {{
  font-size: 14px; font-weight: 500; color: var(--text-secondary);
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 16px;
}}
.metric-value {{ font-size: 40px; font-weight: 300; color: var(--text-primary); letter-spacing: -0.04em; line-height: 1; text-shadow: 0 0 20px rgba(255,255,255,0.2); }}
.metric-unit {{ font-size: 15px; color: var(--text-secondary); margin-left: 6px; font-weight: 400; }}
.metric-delta {{ font-size: 13px; margin-top: 10px; font-weight: 600; padding: 4px 10px; border-radius: 8px; display: inline-block; background: rgba(0,0,0,0.2); }}
.delta-up {{ color: var(--accent-pink); border: 1px solid rgba(236, 72, 153, 0.2); }}
.delta-ok {{ color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.2); }}

/* ── Stress section ── */
.stress-section {{
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  padding: 2rem;
  margin-bottom: 2.5rem;
  box-shadow: 0 15px 35px rgba(0,0,0,0.2);
}}
.stress-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }}
.stress-title {{ font-size: 18px; font-weight: 600; color: var(--text-primary); }}
.stress-badge {{ padding: 6px 16px; border-radius: 100px; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
.badge-relaxed  {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.3); text-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }}
.badge-mild     {{ background: rgba(249, 115, 22, 0.15); color: var(--accent-orange); border: 1px solid rgba(249, 115, 22, 0.3); text-shadow: 0 0 10px rgba(249, 115, 22, 0.4); }}
.badge-moderate {{ background: rgba(236, 72, 153, 0.15); color: var(--accent-pink); border: 1px solid rgba(236, 72, 153, 0.3); text-shadow: 0 0 10px rgba(236, 72, 153, 0.4); }}
.badge-high     {{ background: rgba(225, 29, 72, 0.15); color: #e11d48; border: 1px solid rgba(225, 29, 72, 0.4); text-shadow: 0 0 10px rgba(225, 29, 72, 0.5); box-shadow: 0 0 20px rgba(225, 29, 72, 0.2); }}
.stress-score-row {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 16px; }}
.stress-num {{ font-size: 64px; font-weight: 300; color: var(--text-primary); letter-spacing: -0.05em; line-height: 1; }}
.stress-denom {{ font-size: 18px; color: var(--text-secondary); }}
.stress-bar-bg {{ height: 10px; background: rgba(0,0,0,0.4); border-radius: 10px; overflow: hidden; margin-bottom: 12px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.5); }}
.stress-bar-fill {{
  height: 100%; border-radius: 10px;
  background: linear-gradient(90deg, var(--accent-emerald) 0%, var(--accent-orange) 50%, #e11d48 100%);
  width: {stress_score}%;
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 15px rgba(255,255,255,0.2);
}}
.stress-scale {{
  display: flex; justify-content: space-between;
  font-size: 12px; color: var(--text-secondary); font-family: 'Space Mono', monospace; font-weight: 500;
}}

/* ── Chart ── */
.chart-area {{ margin-top: 2.5rem; border-top: 1px solid var(--glass-border); padding-top: 1.5rem; }}
.chart-sublabel {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }}
.chart-wrap {{ position: relative; width: 100%; height: 180px; }}

/* ── Intervention ── */
.intervention-card {{
  display: {intervention_display};
  background: linear-gradient(145deg, rgba(236, 72, 153, 0.08), rgba(225, 29, 72, 0.03));
  backdrop-filter: blur(16px);
  border: 1px solid rgba(236, 72, 153, 0.3);
  border-radius: 20px;
  padding: 2rem;
  margin-bottom: 2.5rem;
  box-shadow: 0 0 40px rgba(236, 72, 153, 0.1);
}}
.intervention-header {{ display: flex; align-items: center; gap: 14px; margin-bottom: 1.5rem; }}
.alert-dot {{
  width: 12px; height: 12px; border-radius: 50%;
  background: var(--accent-pink); flex-shrink: 0;
  box-shadow: 0 0 15px var(--accent-pink), 0 0 30px var(--accent-pink);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: .5; transform: scale(0.7); }}
}}
.intervention-title {{ font-size: 18px; font-weight: 600; color: var(--text-primary); text-shadow: 0 0 10px rgba(236, 72, 153, 0.3); }}
.trigger-pills {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 2rem; }}
.trigger-pill {{
  padding: 6px 14px;
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(236, 72, 153, 0.2);
  border-radius: 8px;
  font-size: 13px; font-weight: 500; color: #fbcfe8;
}}
.exercise-tabs {{ display: flex; gap: 10px; margin-bottom: 1.5rem; }}
.ex-tab {{
  padding: 10px 20px;
  border-radius: 10px; font-size: 14px; font-weight: 600;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(0,0,0,0.2); color: var(--text-secondary);
  cursor: pointer; font-family: 'Outfit', sans-serif;
  transition: all 0.2s;
}}
.ex-tab:hover {{ background: rgba(255,255,255,0.05); color: var(--text-primary); }}
.ex-tab.active {{ background: rgba(236, 72, 153, 0.15); border-color: rgba(236, 72, 153, 0.4); color: var(--accent-pink); box-shadow: 0 0 20px rgba(236, 72, 153, 0.1); }}
.exercise-content {{
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}}
.breathing-viz {{ display: flex; align-items: center; gap: 30px; }}
.breath-circle {{
  width: 80px; height: 80px; border-radius: 50%;
  border: 2px solid var(--accent-pink);
  background: rgba(236, 72, 153, 0.1);
  flex-shrink: 0;
  animation: breathe 4s ease-in-out infinite;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: var(--accent-pink);
  text-transform: uppercase; letter-spacing: 0.1em;
}}
@keyframes breathe {{
  0%, 100% {{ transform: scale(0.85); box-shadow: 0 0 0 rgba(236,72,153,0); }}
  50% {{ transform: scale(1.15); box-shadow: 0 0 30px rgba(236,72,153,0.4); }}
}}
.breath-steps {{ display: flex; flex-direction: column; gap: 12px; }}
.breath-step {{ font-size: 14px; color: #e2e8f0; display: flex; align-items: center; gap: 12px; }}
.step-num {{
  width: 24px; height: 24px; border-radius: 6px;
  background: rgba(255,255,255,0.1); color: var(--text-primary);
  font-size: 12px; font-weight: 700; font-family: 'Space Mono', monospace;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  border: 1px solid rgba(255,255,255,0.1);
}}
.btn-complete {{
  width: 100%; padding: 14px;
  background: linear-gradient(90deg, var(--accent-pink), #e11d48); color: #fff;
  border: none; border-radius: 12px;
  font-size: 15px; font-weight: 600; letter-spacing: 0.02em;
  cursor: pointer; font-family: 'Outfit', sans-serif;
  transition: opacity 0.2s, transform 0.1s, box-shadow 0.2s;
  box-shadow: 0 4px 15px rgba(225, 29, 72, 0.3);
}}
.btn-complete:hover {{ opacity: 0.9; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(225, 29, 72, 0.4); }}
.btn-complete:active {{ transform: translateY(0); }}

/* ── Bottom row ── */
.bottom-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 2.5rem; }}
.mini-card {{
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-radius: 20px; padding: 1.5rem;
  box-shadow: 0 10px 30px rgba(0,0,0,0.15);
}}
.mini-title {{ font-size: 13px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1.25rem; }}
.emotion-display {{ display: flex; align-items: center; gap: 20px; }}
.emotion-orb {{
  width: 56px; height: 56px; border-radius: 16px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.2));
  border: 1px solid rgba(139, 92, 246, 0.3);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
  box-shadow: 0 8px 20px rgba(139, 92, 246, 0.15);
}}
.emotion-name {{ font-size: 24px; font-weight: 600; color: var(--text-primary); letter-spacing: -0.02em; }}
.emotion-dur {{ font-size: 13px; color: var(--accent-cyan); font-family: 'Space Mono', monospace; margin-top: 6px; }}
.stat-row {{ display: flex; justify-content: space-between; font-size: 14px; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }}
.stat-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
.stat-key {{ color: var(--text-secondary); }}
.stat-val {{ font-weight: 600; color: var(--text-primary); font-family: 'Space Mono', monospace; }}

/* ── Feedback ── */
.feedback-row {{ display: flex; gap: 16px; margin-top: 1.25rem; }}
.btn-feedback {{
  flex: 1; padding: 12px; border-radius: 10px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  font-family: 'Outfit', sans-serif; transition: all 0.2s;
}}
.btn-yes {{ background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: var(--accent-emerald); box-shadow: 0 4px 15px rgba(16, 185, 129, 0.1); }}
.btn-yes:hover {{ background: rgba(16, 185, 129, 0.25); transform: translateY(-1px); }}
.btn-no  {{ background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: var(--text-secondary); }}
.btn-no:hover {{ background: rgba(255,255,255,0.05); color: var(--text-primary); }}
</style>
</head>
<body>
<div class="shell">
  <!-- Top bar -->
  <div class="topbar">
    <div class="brand">
      <div class="brand-icon">
        <svg viewBox="0 0 24 24"><path d="M12 2C8 2 5 5 5 9c0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>
      </div>
      <div>
        <div class="brand-name">MindTrack</div>
        <span class="brand-sub">Context-Aware Assistant</span>
      </div>
    </div>
    <div class="topbar-right">
      <div class="user-chip">
        <div class="avatar">{user_initials}</div>
        {user["name"]}
      </div>
    </div>
  </div>

  <!-- Eye-break banner -->
  <div class="eye-break">
    <div class="eye-left">
      <div style="font-size:28px; opacity: 0.9; filter: drop-shadow(0 0 8px rgba(6,182,212,0.6));">👁</div>
      <div>
        <div class="eye-title">20-20-20 Rule Active</div>
        <div class="eye-desc">Look at something 20 feet away to reduce eye strain.</div>
      </div>
    </div>
    <div class="break-progress-wrap">
      <div class="break-bar-bg"><div class="break-bar-fill"></div></div>
      <div class="break-timer">{break_remaining}s rem</div>
    </div>
  </div>

  <!-- Metrics row -->
  <div class="section-label">Live Telemetry</div>
  <div class="metrics-grid">
    <div class="metric-card" style="--ac: var(--accent-cyan); --ac-glow: rgba(6, 182, 212, 0.08);">
      <div class="metric-label">Typing Velocity</div>
      <div><span class="metric-value">{data.get("current_wpm", 0)}</span><span class="metric-unit">wpm</span></div>
      <div class="metric-delta {'delta-up' if '+' in wpm_delta else 'delta-ok'}">{wpm_delta}</div>
    </div>
    <div class="metric-card" style="--ac: var(--accent-pink); --ac-glow: rgba(236, 72, 153, 0.08);">
      <div class="metric-label">Error Rate</div>
      <div><span class="metric-value">{typo_pct:.1f}</span><span class="metric-unit">%</span></div>
      <div class="metric-delta {typo_class}">{typo_delta}</div>
    </div>
    <div class="metric-card" style="--ac: var(--accent-violet); --ac-glow: rgba(139, 92, 246, 0.08);">
      <div class="metric-label">Backspaces</div>
      <div><span class="metric-value">{data.get("backspace_count", 0)}</span><span class="metric-unit">total</span></div>
      <div class="metric-delta {'delta-up' if '+' in bs_delta else 'delta-ok'}">{bs_delta}</div>
    </div>
  </div>

  <!-- Stress section -->
  <div class="stress-section">
    <div class="stress-header">
      <div class="stress-title">Real-time Cognitive Load</div>
      <div class="stress-badge {level_info['cls']}">{level_info['label']}</div>
    </div>
    <div class="stress-score-row">
      <div class="stress-num">{stress_score}</div>
      <div class="stress-denom">/ 100</div>
    </div>
    <div class="stress-bar-bg"><div class="stress-bar-fill"></div></div>
    <div class="stress-scale">
      <span>Relaxed</span><span>Mild</span><span>Moderate</span><span>Elevated</span>
    </div>
    <div class="chart-area">
      <div class="chart-sublabel">Trend — Last 60 Readings</div>
      <div class="chart-wrap"><canvas id="stressChart"></canvas></div>
    </div>
  </div>

  <!-- Intervention panel -->
  <div class="intervention-card">
    <div class="intervention-header">
      <div class="alert-dot"></div>
      <div class="intervention-title">Elevated Cognitive Load Detected</div>
    </div>
    <div class="trigger-pills">{trigger_pills_html}</div>
    <div class="exercise-tabs">
      <button class="ex-tab active" onclick="switchTab(this,'breathing')">Box Breathing</button>
      <button class="ex-tab" onclick="switchTab(this,'posture')">Posture Check</button>
      <button class="ex-tab" onclick="switchTab(this,'break')">Screen Break</button>
    </div>
    <div class="exercise-content" id="exerciseContent">
      <div class="breathing-viz">
        <div class="breath-circle" id="breathCircle">inhale</div>
        <div class="breath-steps">
          <div class="breath-step"><span class="step-num">1</span>Inhale for 4 seconds</div>
          <div class="breath-step"><span class="step-num">2</span>Hold for 4 seconds</div>
          <div class="breath-step"><span class="step-num">3</span>Exhale for 4 seconds</div>
          <div class="breath-step"><span class="step-num">4</span>Hold for 4 seconds · repeat 3×</div>
        </div>
      </div>
    </div>
    <button class="btn-complete" id="doneBtn" onclick="document.getElementById('feedbackRow').style.display='flex';this.style.display='none'">
      Acknowledge & Complete
    </button>
    <div class="feedback-row" id="feedbackRow" style="display:none">
      <button class="btn-feedback btn-yes">Helpful</button>
      <button class="btn-feedback btn-no">Dismiss</button>
    </div>
  </div>

  <!-- Bottom row -->
  <div class="bottom-row">
    <div class="mini-card">
      <div class="mini-title">Detected Emotion</div>
      <div class="emotion-display">
        <div class="emotion-orb">{emotion_em}</div>
        <div>
          <div class="emotion-name">{emotion_str}</div>
          <div class="emotion-dur">{emotion_dur}s sustained state</div>
        </div>
      </div>
    </div>
    <div class="mini-card">
      <div class="mini-title">Session Overview</div>
      <div class="stat-row"><span class="stat-key">Duration</span><span class="stat-val">{int(session_minutes)}m</span></div>
      <div class="stat-row"><span class="stat-key">Frustration Deletes</span><span class="stat-val">{data.get("frustration_deletes", 0)}</span></div>
      <div class="stat-row"><span class="stat-key">Micro-pauses</span><span class="stat-val">{data.get("pause_count", 0)}</span></div>
      <div class="stat-row"><span class="stat-key">Rhythm Variance</span><span class="stat-val">{data.get("rhythm_variability", 0.0):.2f}</span></div>
    </div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const chartData = {chart_json};
const labels = chartData.map((_, i) => i);

// Create gradient for the chart
const ctx = document.getElementById('stressChart').getContext('2d');
let gradient = ctx.createLinearGradient(0, 0, 0, 180);
gradient.addColorStop(0, 'rgba(139, 92, 246, 0.4)');
gradient.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

new Chart(ctx, {{
  type: 'line',
  data: {{
    labels,
    datasets: [{{
      data: chartData,
      borderColor: '#8b5cf6',
      backgroundColor: gradient,
      borderWidth: 3,
      pointRadius: 0,
      fill: true,
      tension: 0.4
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#94a3b8',
        bodyColor: '#f8fafc',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        padding: 10,
        callbacks: {{ title: () => '', label: ctx => 'Score: ' + ctx.parsed.y }}
      }}
    }},
    scales: {{
      x: {{ display: false }},
      y: {{
        min: 0, max: 100,
        ticks: {{ font: {{ size: 11, family: 'Space Mono' }}, color: '#64748b', maxTicksLimit: 5 }},
        grid: {{ color: 'rgba(255,255,255,0.03)' }},
        border: {{ display: false }}
      }}
    }}
  }}
}});

const breathLabels = ['inhale', 'hold', 'exhale', 'hold'];
let breathIdx = 0;
const bc = document.getElementById('breathCircle');
if (bc) {{
  setInterval(() => {{
    breathIdx = (breathIdx + 1) % 4;
    bc.textContent = breathLabels[breathIdx];
  }}, 4000);
}}

const exerciseContents = {{
  breathing: `<div class="breathing-viz">
    <div class="breath-circle" style="animation:breathe 4s ease-in-out infinite;width:80px;height:80px;border-radius:50%;border:2px solid var(--accent-pink);background:rgba(236,72,153,0.1);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:var(--accent-pink);text-transform:uppercase;letter-spacing:0.1em;flex-shrink:0;">inhale</div>
    <div class="breath-steps">
      <div class="breath-step"><span class="step-num">1</span>Inhale for 4 seconds</div>
      <div class="breath-step"><span class="step-num">2</span>Hold for 4 seconds</div>
      <div class="breath-step"><span class="step-num">3</span>Exhale for 4 seconds</div>
      <div class="breath-step"><span class="step-num">4</span>Hold for 4 seconds · repeat 3×</div>
    </div></div>`,
  posture: `<div class="breath-steps">
    <div class="breath-step"><span class="step-num">1</span>Sit up straight, roll your shoulders back</div>
    <div class="breath-step"><span class="step-num">2</span>Drop tension from your jaw and neck</div>
    <div class="breath-step"><span class="step-num">3</span>Look 20 feet away for 20 seconds</div>
    <div class="breath-step"><span class="step-num">4</span>Adjust your screen to eye level if needed</div>
  </div>`,
  break: `<div class="breath-steps">
    <div class="breath-step"><span class="step-num">1</span>Step away from the screen for 5 minutes</div>
    <div class="breath-step"><span class="step-num">2</span>Stretch your wrists, neck, and shoulders</div>
    <div class="breath-step"><span class="step-num">3</span>Drink a glass of water</div>
    <div class="breath-step"><span class="step-num">4</span>Take a short walk if possible</div>
  </div>`
}};

function switchTab(el, type) {{
  document.querySelectorAll('.ex-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const c = document.getElementById('exerciseContent');
  if (c) c.innerHTML = exerciseContents[type] || '';
  const btn = document.getElementById('doneBtn');
  const fb = document.getElementById('feedbackRow');
  if (btn) {{ btn.style.display = 'block'; }}
  if (fb) {{ fb.style.display = 'none'; }}
}}
</script>
</body>
</html>
"""

# End session button (outside the HTML iframe, using Streamlit)
col_end, _ = st.columns([1, 6])
with col_end:
    if st.button("⏹ End Session", key="end_session_btn", use_container_width=True):
        compute_and_update_baseline(st.session_state.user_id, st.session_state.session_id)
        end_session(st.session_state.session_id)
        st.session_state.user_id = None
        st.session_state.session_id = None
        st.rerun()

# Render the full dashboard
components.html(html, height=1350, scrolling=True)

# Feedback logic (below the iframe using Streamlit)
if show_intervention and st.session_state.intervention_pending_feedback:
    st.markdown("### Was the intervention helpful?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, it helped", key="fb_yes", use_container_width=True):
            save_feedback(st.session_state.last_intervention_id, True)
            st.session_state.intervention_pending_feedback = False
            st.success("Great! Glad it helped.")
            st.rerun()
    with c2:
        if st.button("Not really", key="fb_no", use_container_width=True):
            save_feedback(st.session_state.last_intervention_id, False)
            st.session_state.intervention_pending_feedback = False
            st.rerun()