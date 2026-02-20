import os
import sqlite3
from datetime import datetime
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(Config.DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS area (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department_code TEXT NOT NULL,
            charge_code TEXT
        );

        CREATE TABLE IF NOT EXISTS time_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            area_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(area_id) REFERENCES area(id)
        );

        CREATE TABLE IF NOT EXISTS ts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            description TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            category TEXT,
            FOREIGN KEY(user_id) REFERENCES user(id)
        );
        """
    )
    db.commit()

    # Seed areas if empty
    cur = db.execute("SELECT COUNT(*) AS c FROM area")
    if cur.fetchone()["c"] == 0:
        areas = [
            ("Vigilance Focus Factory", "60011", "VIG-60011"),
            ("Intrepid Focus Factory", "60013", "INT-60013"),
            ("ESS Chambers", "ESS", "ESS-000"),
            ("E3 Projects", "NPRD", "E3-000"),
            ("Enterprise Focus Factory", "60015", "ENT-60015"),
            ("Freedom Focus Factory", "60017", "FRE-60017"),
            ("Breaks", "NPRD", "BREAK-NPRD"),
            ("Liberty Focus Factory", "60012", "LIB-60012"),
            ("Pioneer Focus Factory", "60014", "PIO-60014"),
            ("Training", "TRAIN", "TRAIN-000"),
        ]
        db.executemany(
            "INSERT INTO area (name, department_code, charge_code) VALUES (?, ?, ?)",
            areas,
        )
        db.commit()

# User helpers

def create_user(username, password):
    db = get_db()
    pwd_hash = generate_password_hash(password)
    db.execute(
        "INSERT INTO user (username, password_hash) VALUES (?, ?)",
        (username, pwd_hash),
    )
    db.commit()

def get_user_by_username(username):
    db = get_db()
    cur = db.execute("SELECT * FROM user WHERE username = ?", (username,))
    return cur.fetchone()

def verify_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None

# Area and time log helpers

def get_areas():
    db = get_db()
    cur = db.execute("SELECT * FROM area ORDER BY name")
    return cur.fetchall()

def get_area_by_id(area_id):
    db = get_db()
    cur = db.execute("SELECT * FROM area WHERE id = ?", (area_id,))
    return cur.fetchone()

def get_active_log(user_id):
    db = get_db()
    cur = db.execute(
        "SELECT * FROM time_log WHERE user_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
        (user_id,),
    )
    return cur.fetchone()

def start_logging(user_id, area_id):
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO time_log (user_id, area_id, start_time) VALUES (?, ?, ?)",
        (user_id, area_id, now),
    )
    db.commit()

def stop_logging(log_id):
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE time_log SET end_time = ? WHERE id = ? AND end_time IS NULL",
        (now, log_id),
    )
    db.commit()

def get_logs_for_range(user_id, start_date, end_date):
    db = get_db()
    query = """
        SELECT tl.*, a.name AS area_name, a.department_code, a.charge_code
        FROM time_log tl
        JOIN area a ON tl.area_id = a.id
        WHERE tl.user_id = ?
          AND date(tl.start_time) BETWEEN date(?) AND date(?)
        ORDER BY tl.start_time
    """
    cur = db.execute(query, (user_id, start_date, end_date))
    return cur.fetchall()

def compute_durations(logs):
    """
    Compute duration (hours) for each log row, returning a list of dicts
    with an added 'duration_hours' key.
    """
    enriched = []
    for row in logs:
        start = datetime.fromisoformat(row["start_time"])
        if row["end_time"]:
            end = datetime.fromisoformat(row["end_time"])
        else:
            end = datetime.utcnow()
        seconds = (end - start).total_seconds()
        hours = seconds / 3600.0
        d = dict(row)
        d["duration_hours"] = hours
        enriched.append(d)
    return enriched

def aggregate_by_area(logs_with_durations):
    """
    Aggregate duration by (area_name, department_code, charge_code)
    returning a dict: (area, dept, charge) -> total_hours
    """
    from collections import defaultdict
    summary = defaultdict(float)
    for row in logs_with_durations:
        key = (row["area_name"], row["department_code"], row["charge_code"])
        summary[key] += row["duration_hours"]
    return summary

# T/S log helpers

def get_active_ts_log(user_id):
    db = get_db()
    cur = db.execute(
        "SELECT * FROM ts_log WHERE user_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
        (user_id,),
    )
    return cur.fetchone()

def start_ts_log(user_id, task_name, description, category):
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO ts_log (user_id, task_name, description, start_time, category) VALUES (?, ?, ?, ?, ?)",
        (user_id, task_name, description, now, category),
    )
    db.commit()

def stop_ts_log(ts_log_id):
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE ts_log SET end_time = ? WHERE id = ? AND end_time IS NULL",
        (now, ts_log_id),
    )
    db.commit()

def get_ts_logs_for_range(user_id, start_date, end_date):
    db = get_db()
    query = """
        SELECT * FROM ts_log
        WHERE user_id = ?
          AND date(start_time) BETWEEN date(?) AND date(?)
        ORDER BY start_time
    """
    cur = db.execute(query, (user_id, start_date, end_date))
    return cur.fetchall()

def compute_ts_durations(logs):
    enriched = []
    for row in logs:
        start = datetime.fromisoformat(row["start_time"])
        if row["end_time"]:
            end = datetime.fromisoformat(row["end_time"])
        else:
            end = datetime.utcnow()
        seconds = (end - start).total_seconds()
        hours = seconds / 3600.0
        d = dict(row)
        d["duration_hours"] = hours
        enriched.append(d)
    return enriched
