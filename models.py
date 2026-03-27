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

        CREATE TABLE IF NOT EXISTS charge_code (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS area (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            charge_code_id INTEGER,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(charge_code_id) REFERENCES charge_code(id)
        );

        CREATE TABLE IF NOT EXISTS time_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            area_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(id)
        );
        """
    )
    db.commit()

    # Seed charge codes if empty
    cur = db.execute("SELECT COUNT(*) AS c FROM charge_code")
    if cur.fetchone()["c"] == 0:
        charge_codes = [
            ("VIG-60011", "Vigilance Focus Factory"),
            ("INT-60013", "Intrepid Focus Factory"),
            ("ESS-000", "ESS Chambers"),
            ("E3-000", "E3 Projects"),
            ("ENT-60015", "Enterprise Focus Factory"),
            ("FRE-60017", "Freedom Focus Factory"),
            ("BREAK-NPRD", "Breaks"),
            ("LIB-60012", "Liberty Focus Factory"),
            ("PIO-60014", "Pioneer Focus Factory"),
            ("TRAIN-000", "Training"),
        ]
        db.executemany(
            "INSERT INTO charge_code (code, description) VALUES (?, ?)",
            charge_codes,
        )
        db.commit()

    # Seed areas if empty
    cur = db.execute("SELECT COUNT(*) AS c FROM area")
    if cur.fetchone()["c"] == 0:
        areas = [
            ("Vigilance Focus Factory", 1, "Main production area for Vigilance"),
            ("Intrepid Focus Factory", 2, "Main production area for Intrepid"),
            ("ESS Chambers", 3, "Environmental testing chambers"),
            ("E3 Projects", 4, "Engineering projects area"),
            ("Enterprise Focus Factory", 5, "Main production area for Enterprise"),
            ("Freedom Focus Factory", 6, "Main production area for Freedom"),
            ("Breaks", 7, "Break areas and lunch rooms"),
            ("Liberty Focus Factory", 8, "Main production area for Liberty"),
            ("Pioneer Focus Factory", 9, "Main production area for Pioneer"),
            ("Training", 10, "Training and meeting rooms"),
        ]
        db.executemany(
            "INSERT INTO area (name, charge_code_id, description) VALUES (?, ?, ?)",
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
        SELECT tl.*, a.name AS area_name, a.description AS area_description,
               cc.code AS charge_code, cc.description AS charge_code_description
        FROM time_log tl
        JOIN area a ON tl.area_id = a.id
        LEFT JOIN charge_code cc ON a.charge_code_id = cc.id
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
    Aggregate duration by (area_name, charge_code, charge_code_description)
    returning a dict: (area, charge_code, description) -> total_hours
    """
    from collections import defaultdict
    summary = defaultdict(float)
    for row in logs_with_durations:
        key = (row["area_name"], row["charge_code"] or "No Charge Code", row["charge_code_description"] or "")
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

# Charge code management functions

def get_charge_codes():
    """Get all charge codes ordered by code"""
    db = get_db()
    cur = db.execute("SELECT * FROM charge_code ORDER BY code")
    return cur.fetchall()

def get_charge_code_by_id(charge_code_id):
    """Get a charge code by ID"""
    db = get_db()
    cur = db.execute("SELECT * FROM charge_code WHERE id = ?", (charge_code_id,))
    return cur.fetchone()

def create_charge_code(code, description):
    """Create a new charge code"""
    db = get_db()
    db.execute(
        "INSERT INTO charge_code (code, description) VALUES (?, ?)",
        (code, description),
    )
    db.commit()

def update_charge_code(charge_code_id, code, description):
    """Update an existing charge code"""
    db = get_db()
    db.execute(
        "UPDATE charge_code SET code = ?, description = ? WHERE id = ?",
        (code, description, charge_code_id),
    )
    db.commit()

def delete_charge_code(charge_code_id):
    """Delete a charge code (soft delete by setting is_active = 0)"""
    db = get_db()
    db.execute(
        "UPDATE charge_code SET is_active = 0 WHERE id = ?",
        (charge_code_id,),
    )
    db.commit()

# Area management functions

def get_areas_with_charge_codes():
    """Get all areas with their associated charge codes"""
    db = get_db()
    query = """
        SELECT a.*, cc.code as charge_code_code, cc.description as charge_code_description
        FROM area a
        LEFT JOIN charge_code cc ON a.charge_code_id = cc.id
        WHERE a.is_active = 1
        ORDER BY a.name
    """
    cur = db.execute(query)
    return cur.fetchall()

def create_area(name, charge_code_id, description):
    """Create a new area"""
    db = get_db()
    db.execute(
        "INSERT INTO area (name, charge_code_id, description) VALUES (?, ?, ?)",
        (name, charge_code_id or None, description),
    )
    db.commit()

def update_area(area_id, name, charge_code_id, description):
    """Update an existing area"""
    db = get_db()
    db.execute(
        "UPDATE area SET name = ?, charge_code_id = ?, description = ? WHERE id = ?",
        (name, charge_code_id or None, description, area_id),
    )
    db.commit()

def delete_area(area_id):
    """Delete an area (soft delete by setting is_active = 0)"""
    db = get_db()
    db.execute(
        "UPDATE area SET is_active = 0 WHERE id = ?",
        (area_id,),
    )
    db.commit()
