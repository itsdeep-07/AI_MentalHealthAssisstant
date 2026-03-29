import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mental_health.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_baseline (
            baseline_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            avg_wpm REAL DEFAULT 0,
            avg_backspace_rate REAL DEFAULT 0,
            dominant_emotion TEXT DEFAULT 'neutral',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS sensor_readings (
            reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            current_wpm INTEGER DEFAULT 0,
            backspace_count INTEGER DEFAULT 0,
            detected_emotion TEXT DEFAULT 'neutral',
            stress_score INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS stress_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            stress_score INTEGER,
            trigger_type TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS interventions (
            intervention_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            type TEXT,
            content TEXT,
            shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES stress_events(event_id)
        );

        CREATE TABLE IF NOT EXISTS intervention_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            intervention_id INTEGER NOT NULL,
            was_helpful INTEGER,
            responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intervention_id) REFERENCES interventions(intervention_id)
        );
    """)
    conn.commit()
    conn.close()

def create_user(name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (name) VALUES (?)", (name,))
    user_id = c.lastrowid
    c.execute("INSERT INTO user_baseline (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    return user_id

def get_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def start_session(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sessions (user_id) VALUES (?)", (user_id,))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def end_session(session_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE sessions SET end_time = CURRENT_TIMESTAMP, status = 'ended' WHERE session_id = ?",
        (session_id,)
    )
    conn.commit()
    conn.close()

def save_reading(session_id, wpm, backspaces, emotion, stress_score):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sensor_readings (session_id, current_wpm, backspace_count, detected_emotion, stress_score) VALUES (?,?,?,?,?)",
        (session_id, wpm, backspaces, emotion, stress_score)
    )
    conn.commit()
    conn.close()

def log_stress_event(session_id, stress_score, trigger_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO stress_events (session_id, stress_score, trigger_type) VALUES (?,?,?)",
        (session_id, stress_score, trigger_type)
    )
    event_id = c.lastrowid
    conn.commit()
    conn.close()
    return event_id

def log_intervention(event_id, intervention_type, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO interventions (event_id, type, content) VALUES (?,?,?)",
        (event_id, intervention_type, content)
    )
    intervention_id = c.lastrowid
    conn.commit()
    conn.close()
    return intervention_id

def save_feedback(intervention_id, was_helpful):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO intervention_feedback (intervention_id, was_helpful) VALUES (?,?)",
        (intervention_id, 1 if was_helpful else 0)
    )
    conn.commit()
    conn.close()

def get_baseline(user_id):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute(
        "SELECT * FROM user_baseline WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def update_baseline(user_id, avg_wpm, avg_backspace_rate, dominant_emotion):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """UPDATE user_baseline
           SET avg_wpm = ?, avg_backspace_rate = ?, dominant_emotion = ?,
               last_updated = CURRENT_TIMESTAMP
           WHERE user_id = ?""",
        (avg_wpm, avg_backspace_rate, dominant_emotion, user_id)
    )
    conn.commit()
    conn.close()

def get_session_readings(session_id):
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM sensor_readings WHERE session_id = ? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recent_readings(session_id, limit=30):
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM sensor_readings WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def compute_and_update_baseline(user_id, session_id):
    readings = get_session_readings(session_id)
    if len(readings) < 10:
        return
    wpms = [r["current_wpm"] for r in readings if r["current_wpm"] > 0]
    backspaces = [r["backspace_count"] for r in readings]
    emotions = [r["detected_emotion"] for r in readings]
    if not wpms:
        return
    avg_wpm = sum(wpms) / len(wpms)
    avg_bs = sum(backspaces) / len(backspaces)
    dominant = max(set(emotions), key=emotions.count)
    update_baseline(user_id, avg_wpm, avg_bs, dominant)
