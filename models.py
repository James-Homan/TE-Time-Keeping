"""Database models and operations for TE Timekeeping application.

This module provides all database operations for managing:
- Users and authentication
- Time logs (area-based tracking)
- Task/Service logs (task-based tracking)
- Charge codes and areas
"""

import os
import logging
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

logger = logging.getLogger(__name__)

os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)


def get_db() -> sqlite3.Connection:
    """Get the SQLite database connection for the current Flask context.
    
    Returns:
        sqlite3.Connection: Database connection with Row factory enabled.
    """
    if "db" not in g:
        g.db = sqlite3.connect(Config.DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e: Optional[Exception] = None) -> None:
    """Close the database connection.
    
    Args:
        e: Optional exception that triggered the close (used by Flask teardown).
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()
        logger.debug("Database connection closed")


def init_db() -> None:
    """Initialize the database schema and seed initial data."""
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            last_login TEXT,
            failed_login_attempts INTEGER DEFAULT 0,
            is_locked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            attempt_time TEXT NOT NULL,
            success BOOLEAN DEFAULT 0,
            ip_address TEXT,
            FOREIGN KEY(user_id) REFERENCES user(id)
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            favorite_areas TEXT,
            preferred_charge_codes TEXT,
            default_area_id INTEGER,
            theme TEXT DEFAULT 'light',
            timezone TEXT DEFAULT 'UTC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(id)
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

        CREATE TABLE IF NOT EXISTS user_custom_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            area_id INTEGER,
            custom_name TEXT,
            is_favorite BOOLEAN DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(area_id) REFERENCES area(id)
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
            station TEXT,
            problem TEXT,
            solution TEXT,
            description TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT DEFAULT 'Pending',
            priority TEXT DEFAULT 'Low',
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(id)
        );
        """
    )
    db.commit()
    logger.info("Database schema initialized")

    # Run migrations for existing databases
    run_migrations(db)

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
        logger.info(f"Seeded {len(charge_codes)} charge codes")

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


def run_migrations(db: sqlite3.Connection) -> None:
    """Run database migrations to add missing columns/tables to existing databases.

    Args:
        db: Database connection to migrate.
    """
    logger.info("Checking for database migrations...")

    # Check if user table has last_login column
    try:
        cur = db.execute("SELECT last_login FROM user LIMIT 1")
        cur.fetchone()
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        logger.info("Adding last_login column to user table")
        db.execute("ALTER TABLE user ADD COLUMN last_login TEXT")
        db.commit()

    # Check if user table has is_locked column
    try:
        cur = db.execute("SELECT is_locked FROM user LIMIT 1")
        cur.fetchone()
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        logger.info("Adding is_locked column to user table")
        db.execute("ALTER TABLE user ADD COLUMN is_locked BOOLEAN DEFAULT 0")
        db.commit()

    # Check if user table has failed_login_attempts column
    try:
        cur = db.execute("SELECT failed_login_attempts FROM user LIMIT 1")
        cur.fetchone()
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        logger.info("Adding failed_login_attempts column to user table")
        db.execute("ALTER TABLE user ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
        db.commit()

    # Check if ts_log table has required columns
    columns_to_check = ['station', 'problem', 'solution', 'description', 'status', 'priority', 'category', 'updated_at']
    for column in columns_to_check:
        try:
            cur = db.execute(f"SELECT {column} FROM ts_log LIMIT 1")
            cur.fetchone()
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            logger.info(f"Adding {column} column to ts_log table")
            if column == 'updated_at':
                # SQLite does not allow non-constant defaults during ALTER TABLE
                db.execute(f"ALTER TABLE ts_log ADD COLUMN {column} TEXT DEFAULT '1970-01-01 00:00:00'")
            else:
                db.execute(f"ALTER TABLE ts_log ADD COLUMN {column} TEXT")
            db.commit()
            if column == 'updated_at':
                # Backfill old records with current timestamp
                db.execute("UPDATE ts_log SET updated_at = datetime('now') WHERE updated_at IS NULL OR updated_at = ''")
                db.commit()

    # Check if login_attempts table exists
    try:
        cur = db.execute("SELECT COUNT(*) FROM login_attempts")
        cur.fetchone()
    except sqlite3.OperationalError:
        # Table doesn't exist, create it
        logger.info("Creating login_attempts table")
        db.executescript("""
            CREATE TABLE login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                attempt_time TEXT NOT NULL,
                success BOOLEAN DEFAULT 0,
                ip_address TEXT,
                FOREIGN KEY(user_id) REFERENCES user(id)
            );
        """)
        db.commit()

    # Check if user_settings table exists
    try:
        cur = db.execute("SELECT COUNT(*) FROM user_settings")
        cur.fetchone()
    except sqlite3.OperationalError:
        # Table doesn't exist, create it
        logger.info("Creating user_settings table")
        db.executescript("""
            CREATE TABLE user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                favorite_areas TEXT,
                preferred_charge_codes TEXT,
                default_area_id INTEGER,
                theme TEXT DEFAULT 'light',
                timezone TEXT DEFAULT 'UTC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES user(id)
            );
        """)
        db.commit()

    # Check if user_custom_areas table exists
    try:
        cur = db.execute("SELECT COUNT(*) FROM user_custom_areas")
        cur.fetchone()
    except sqlite3.OperationalError:
        # Table doesn't exist, create it
        logger.info("Creating user_custom_areas table")
        db.executescript("""
            CREATE TABLE user_custom_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                area_id INTEGER,
                custom_name TEXT,
                is_favorite BOOLEAN DEFAULT 0,
                display_order INTEGER,
                FOREIGN KEY(user_id) REFERENCES user(id),
                FOREIGN KEY(area_id) REFERENCES area(id)
            );
        """)
        db.commit()

    logger.info("Database migrations completed")


# User helpers

def create_user(username: str, password: str) -> None:
    """Create a new user with hashed password.
    
    Args:
        username: Username for the new account.
        password: Plain text password (will be hashed).
        
    Raises:
        sqlite3.IntegrityError: If username already exists.
    """
    db = get_db()
    pwd_hash = generate_password_hash(password)
    db.execute(
        "INSERT INTO user (username, password_hash) VALUES (?, ?)",
        (username, pwd_hash),
    )
    db.commit()
    logger.info(f"Created new user: {username}")


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    """Get user by username.
    
    Args:
        username: Username to search for.
        
    Returns:
        User row if found, None otherwise.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM user WHERE username = ?", (username,))
    return cur.fetchone()


def verify_user(username: str, password: str) -> Optional[sqlite3.Row]:
    """Verify user credentials.
    
    Args:
        username: Username to verify.
        password: Plain text password to verify.
        
    Returns:
        User row if credentials are valid, None otherwise.
    """
    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


# Area and time log helpers

def get_areas() -> List[sqlite3.Row]:
    """Get all active areas ordered by name.
    
    Returns:
        List of area rows.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM area WHERE is_active = 1 ORDER BY name")
    return cur.fetchall()


def get_area_by_id(area_id: int) -> Optional[sqlite3.Row]:
    """Get area by ID.
    
    Args:
        area_id: Area ID to search for.
        
    Returns:
        Area row if found, None otherwise.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM area WHERE id = ?", (area_id,))
    return cur.fetchone()


def get_active_log(user_id: int) -> Optional[sqlite3.Row]:
    """Get the active (non-completed) time log for a user.
    
    Args:
        user_id: User ID to search for.
        
    Returns:
        Active time log row if one exists, None otherwise.
    """
    db = get_db()
    cur = db.execute(
        "SELECT * FROM time_log WHERE user_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
        (user_id,),
    )
    return cur.fetchone()


def start_logging(user_id: int, area_id: int) -> None:
    """Start a new time log entry.
    
    Args:
        user_id: User ID starting the log.
        area_id: Area ID being logged.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO time_log (user_id, area_id, start_time) VALUES (?, ?, ?)",
        (user_id, area_id, now),
    )
    db.commit()
    logger.debug(f"Time log started for user {user_id} in area {area_id}")


def stop_logging(log_id: int) -> None:
    """Stop/complete an active time log entry.
    
    Args:
        log_id: Time log ID to stop.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE time_log SET end_time = ? WHERE id = ? AND end_time IS NULL",
        (now, log_id),
    )
    db.commit()
    logger.debug(f"Time log {log_id} stopped")


def get_logs_for_range(user_id: int, start_date: str, end_date: str) -> List[sqlite3.Row]:
    """Get time logs for a user within a date range.
    
    Args:
        user_id: User ID to retrieve logs for.
        start_date: Start date (ISO format).
        end_date: End date (ISO format).
        
    Returns:
        List of time log rows with area and charge code information.
    """
    db = get_db()
    query = """
        SELECT tl.*, a.name AS area_name, a.description AS area_description,
               cc.code AS charge_code, cc.description AS charge_code_description,
               COALESCE(cc.code, '') AS department_code
        FROM time_log tl
        JOIN area a ON tl.area_id = a.id
        LEFT JOIN charge_code cc ON a.charge_code_id = cc.id
        WHERE tl.user_id = ?
          AND date(tl.start_time) BETWEEN date(?) AND date(?)
        ORDER BY tl.start_time
    """
    cur = db.execute(query, (user_id, start_date, end_date))
    return cur.fetchall()


def compute_durations(logs: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Compute duration (hours) for each log row.
    
    Args:
        logs: List of time log rows.
        
    Returns:
        List of log dictionaries with added 'duration_hours' key.
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


def aggregate_by_area(logs_with_durations: List[Dict[str, Any]]) -> Dict[tuple, float]:
    """Aggregate duration by area and charge code.
    
    Args:
        logs_with_durations: List of logs with computed durations.
        
    Returns:
        Dictionary mapping (area_name, charge_code, description) -> total_hours.
    """
    from collections import defaultdict
    summary = defaultdict(float)
    for row in logs_with_durations:
        key = (row["area_name"], row.get("department_code", "") or row["charge_code"] or "No Charge Code", row["charge_code_description"] or "")
        summary[key] += row["duration_hours"]
    return summary

# T/S log helpers

def get_active_ts_log(user_id: int) -> Optional[sqlite3.Row]:
    """Get the active (non-completed) task/service log for a user.
    
    Args:
        user_id: User ID to search for.
        
    Returns:
        Active T/S log row if one exists, None otherwise.
    """
    db = get_db()
    cur = db.execute(
        "SELECT * FROM ts_log WHERE user_id = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
        (user_id,),
    )
    return cur.fetchone()


def start_ts_log(user_id: int, task_name: str, description: str, category: str) -> None:
    """Start a new task/service log entry.
    
    Args:
        user_id: User ID starting the log.
        task_name: Name of the task.
        description: Task description.
        category: Task category.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO ts_log (user_id, task_name, description, start_time, category) VALUES (?, ?, ?, ?, ?)",
        (user_id, task_name, description, now, category),
    )
    db.commit()
    logger.debug(f"T/S log started for user {user_id}: {task_name}")


def stop_ts_log(ts_log_id: int) -> None:
    """Stop/complete an active task/service log entry.
    
    Args:
        ts_log_id: T/S log ID to stop.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "UPDATE ts_log SET end_time = ? WHERE id = ? AND end_time IS NULL",
        (now, ts_log_id),
    )
    db.commit()
    logger.debug(f"T/S log {ts_log_id} stopped")


def get_ts_logs_for_range(user_id: int, start_date: str, end_date: str) -> List[sqlite3.Row]:
    """Get T/S logs for a user within a date range.
    
    Args:
        user_id: User ID to retrieve logs for.
        start_date: Start date (ISO format).
        end_date: End date (ISO format).
        
    Returns:
        List of T/S log rows.
    """
    db = get_db()
    query = """
        SELECT * FROM ts_log
        WHERE user_id = ?
          AND date(start_time) BETWEEN date(?) AND date(?)
        ORDER BY start_time
    """
    cur = db.execute(query, (user_id, start_date, end_date))
    return cur.fetchall()


def compute_ts_durations(logs: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Compute duration (hours) for each T/S log row.
    
    Args:
        logs: List of T/S log rows.
        
    Returns:
        List of log dictionaries with added 'duration_hours' key.
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


# Charge code management functions

def get_charge_codes() -> List[sqlite3.Row]:
    """Get all active charge codes ordered by code.
    
    Returns:
        List of charge code rows.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM charge_code WHERE is_active = 1 ORDER BY code")
    return cur.fetchall()


def get_charge_code_by_id(charge_code_id: int) -> Optional[sqlite3.Row]:
    """Get a charge code by ID.
    
    Args:
        charge_code_id: Charge code ID to search for.
        
    Returns:
        Charge code row if found, None otherwise.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM charge_code WHERE id = ?", (charge_code_id,))
    return cur.fetchone()


def create_charge_code(code: str, description: str) -> None:
    """Create a new charge code.
    
    Args:
        code: Charge code (must be unique).
        description: Description of the charge code.
        
    Raises:
        sqlite3.IntegrityError: If code already exists.
    """
    db = get_db()
    db.execute(
        "INSERT INTO charge_code (code, description) VALUES (?, ?)",
        (code, description),
    )
    db.commit()
    logger.info(f"Created charge code: {code}")


def update_charge_code(charge_code_id: int, code: str, description: str) -> None:
    """Update an existing charge code.
    
    Args:
        charge_code_id: Charge code ID to update.
        code: New charge code.
        description: New description.
    """
    db = get_db()
    db.execute(
        "UPDATE charge_code SET code = ?, description = ? WHERE id = ?",
        (code, description, charge_code_id),
    )
    db.commit()
    logger.info(f"Updated charge code {charge_code_id}: {code}")


def delete_charge_code(charge_code_id: int) -> None:
    """Delete a charge code (soft delete by setting is_active = 0).
    
    Args:
        charge_code_id: Charge code ID to delete.
    """
    db = get_db()
    db.execute(
        "UPDATE charge_code SET is_active = 0 WHERE id = ?",
        (charge_code_id,),
    )
    db.commit()
    logger.info(f"Deleted charge code {charge_code_id}")


# Area management functions

def get_areas_with_charge_codes() -> List[sqlite3.Row]:
    """Get all active areas with their associated charge codes.
    
    Returns:
        List of area rows with charge code information.
    """
    db = get_db()
    query = """
        SELECT a.*, cc.code AS department_code, cc.code AS charge_code, cc.description AS charge_code_description
        FROM area a
        LEFT JOIN charge_code cc ON a.charge_code_id = cc.id
        WHERE a.is_active = 1
        ORDER BY a.name
    """
    cur = db.execute(query)
    return cur.fetchall()


def create_area(name: str, charge_code_id: Optional[int], description: str) -> None:
    """Create a new area.
    
    Args:
        name: Area name.
        charge_code_id: Optional charge code ID.
        description: Area description.
    """
    db = get_db()
    db.execute(
        "INSERT INTO area (name, charge_code_id, description) VALUES (?, ?, ?)",
        (name, charge_code_id or None, description),
    )
    db.commit()
    logger.info(f"Created area: {name}")


def update_area(area_id: int, name: str, charge_code_id: Optional[int], description: str) -> None:
    """Update an existing area.
    
    Args:
        area_id: Area ID to update.
        name: New area name.
        charge_code_id: New optional charge code ID.
        description: New description.
    """
    db = get_db()
    db.execute(
        "UPDATE area SET name = ?, charge_code_id = ?, description = ? WHERE id = ?",
        (name, charge_code_id or None, description, area_id),
    )
    db.commit()
    logger.info(f"Updated area {area_id}: {name}")


def delete_area(area_id: int) -> None:
    """Delete an area (soft delete by setting is_active = 0).
    
    Args:
        area_id: Area ID to delete.
    """
    db = get_db()
    db.execute(
        "UPDATE area SET is_active = 0 WHERE id = ?",
        (area_id,),
    )
    db.commit()
    logger.info(f"Deleted area {area_id}")


# Rate limiting and security functions

def record_login_attempt(user_id: int, success: bool, ip_address: str = None) -> None:
    """Record a login attempt for rate limiting and security monitoring.
    
    Args:
        user_id: User ID attempting login.
        success: Whether the login attempt was successful.
        ip_address: Optional IP address of the attempt.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO login_attempts (user_id, attempt_time, success, ip_address) VALUES (?, ?, ?, ?)",
        (user_id, now, success, ip_address),
    )
    db.commit()
    logger.debug(f"Recorded login attempt for user {user_id}: success={success}")


def get_recent_failed_attempts(user_id: int, minutes: int = 15) -> int:
    """Get count of failed login attempts in recent time period.
    
    Args:
        user_id: User ID to check.
        minutes: Time window in minutes (default 15).
        
    Returns:
        Count of failed attempts in the time window.
    """
    db = get_db()
    # Calculate time window start
    from datetime import timedelta
    cutoff_time = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
    
    cur = db.execute(
        "SELECT COUNT(*) as count FROM login_attempts WHERE user_id = ? AND success = 0 AND attempt_time > ?",
        (user_id, cutoff_time),
    )
    return cur.fetchone()["count"]


def lock_user_account(user_id: int) -> None:
    """Lock a user account (typically after too many failed attempts).
    
    Args:
        user_id: User ID to lock.
    """
    db = get_db()
    db.execute("UPDATE user SET is_locked = 1 WHERE id = ?", (user_id,))
    db.commit()
    logger.warning(f"Locked user account {user_id}")


def unlock_user_account(user_id: int) -> None:
    """Unlock a user account.
    
    Args:
        user_id: User ID to unlock.
    """
    db = get_db()
    db.execute("UPDATE user SET is_locked = 0, failed_login_attempts = 0 WHERE id = ?", (user_id,))
    db.commit()
    logger.info(f"Unlocked user account {user_id}")


def is_user_locked(user_id: int) -> bool:
    """Check if a user account is locked.
    
    Args:
        user_id: User ID to check.
        
    Returns:
        True if account is locked, False otherwise.
    """
    db = get_db()
    cur = db.execute("SELECT is_locked FROM user WHERE id = ?", (user_id,))
    row = cur.fetchone()
    return row["is_locked"] == 1 if row else False


def update_user_last_login(user_id: int) -> None:
    """Update the user's last login timestamp.
    
    Args:
        user_id: User ID to update.
    """
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute("UPDATE user SET last_login = ? WHERE id = ?", (now, user_id))
    db.commit()
    logger.debug(f"Updated last login for user {user_id}")


# User preferences functions

def get_user_settings(user_id: int) -> Optional[sqlite3.Row]:
    """Get user preferences/settings.
    
    Args:
        user_id: User ID to retrieve settings for.
        
    Returns:
        User settings row if found, None otherwise.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    return cur.fetchone()


def create_user_settings(user_id: int) -> None:
    """Create default user settings for a new user.
    
    Args:
        user_id: User ID to create settings for.
    """
    db = get_db()
    db.execute(
        "INSERT INTO user_settings (user_id) VALUES (?)",
        (user_id,),
    )
    db.commit()
    logger.debug(f"Created default settings for user {user_id}")


def update_user_settings(user_id: int, **kwargs) -> None:
    """Update user preferences/settings.
    
    Args:
        user_id: User ID to update.
        **kwargs: Settings to update (favorite_areas, preferred_charge_codes, default_area_id, theme, timezone).
    """
    db = get_db()
    allowed_fields = {'favorite_areas', 'preferred_charge_codes', 'default_area_id', 'theme', 'timezone'}
    
    # Build update query dynamically
    fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
    
    if not fields_to_update:
        logger.warning(f"No valid fields to update for user {user_id}")
        return
    
    # Add updated_at timestamp
    fields_to_update['updated_at'] = datetime.utcnow().isoformat()
    
    # Build WHERE clause and values
    set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [user_id]
    
    query = f"UPDATE user_settings SET {set_clause} WHERE user_id = ?"
    db.execute(query, values)
    db.commit()
    logger.info(f"Updated settings for user {user_id}: {list(fields_to_update.keys())}")


def get_user_custom_areas(user_id: int) -> List[sqlite3.Row]:
    """Get user's customized areas.
    
    Args:
        user_id: User ID to retrieve custom areas for.
        
    Returns:
        List of custom area rows.
    """
    db = get_db()
    cur = db.execute(
        """
        SELECT uca.*, a.name as area_name, a.description as area_description
        FROM user_custom_areas uca
        LEFT JOIN area a ON uca.area_id = a.id
        WHERE uca.user_id = ?
        ORDER BY uca.display_order, uca.is_favorite DESC, a.name
        """,
        (user_id,),
    )
    return cur.fetchall()


def add_user_custom_area(user_id: int, area_id: int, custom_name: str = None, is_favorite: bool = False, display_order: int = 0) -> None:
    """Add a custom area entry for a user.
    
    Args:
        user_id: User ID.
        area_id: Area ID to customize.
        custom_name: Optional custom name for the area.
        is_favorite: Whether to mark as favorite.
        display_order: Display order preference.
    """
    db = get_db()
    db.execute(
        "INSERT INTO user_custom_areas (user_id, area_id, custom_name, is_favorite, display_order) VALUES (?, ?, ?, ?, ?)",
        (user_id, area_id, custom_name, is_favorite, display_order),
    )
    db.commit()
    logger.debug(f"Added custom area for user {user_id}: area {area_id}")


def update_user_custom_area(custom_area_id: int, custom_name: str = None, is_favorite: bool = None, display_order: int = None) -> None:
    """Update a user's custom area setting.
    
    Args:
        custom_area_id: Custom area ID to update.
        custom_name: New custom name (optional).
        is_favorite: New favorite status (optional).
        display_order: New display order (optional).
    """
    db = get_db()
    updates = {}
    if custom_name is not None:
        updates['custom_name'] = custom_name
    if is_favorite is not None:
        updates['is_favorite'] = is_favorite
    if display_order is not None:
        updates['display_order'] = display_order
    
    if not updates:
        return
    
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [custom_area_id]
    query = f"UPDATE user_custom_areas SET {set_clause} WHERE id = ?"
    db.execute(query, values)
    db.commit()
    logger.debug(f"Updated custom area {custom_area_id}")


# Enhanced T/S log functions

def update_ts_log_with_details(ts_log_id: int, station: str = None, problem: str = None, solution: str = None, status: str = None, priority: str = None) -> None:
    """Update a T/S log entry with detailed tracking information.
    
    Args:
        ts_log_id: T/S log ID to update.
        station: Station/location information.
        problem: Problem description.
        solution: Solution implemented.
        status: Task status (Pending/In Progress/Completed).
        priority: Priority level (Low/Medium/High).
    """
    db = get_db()
    updates = {}
    if station is not None:
        updates['station'] = station
    if problem is not None:
        updates['problem'] = problem
    if solution is not None:
        updates['solution'] = solution
    if status is not None:
        updates['status'] = status
    if priority is not None:
        updates['priority'] = priority
    
    if not updates:
        return
    
    updates['updated_at'] = datetime.utcnow().isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [ts_log_id]
    query = f"UPDATE ts_log SET {set_clause} WHERE id = ?"
    db.execute(query, values)
    db.commit()
    logger.debug(f"Updated T/S log {ts_log_id} with detailed information")


def get_ts_log_by_id(ts_log_id: int) -> Optional[sqlite3.Row]:
    """Get a specific T/S log entry by ID.
    
    Args:
        ts_log_id: T/S log ID to retrieve.
        
    Returns:
        T/S log row if found, None otherwise.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM ts_log WHERE id = ?", (ts_log_id,))
    return cur.fetchone()


def get_dashboard_summary(user_id: int, days_back: int = 1) -> Dict[str, Any]:
    """Get comprehensive dashboard summary for a user.
    
    Args:
        user_id: User ID to get summary for.
        days_back: Number of days to look back (default 1 for current day).
        
    Returns:
        Dictionary with dashboard metrics including total time, active logs, area breakdown.
    """
    db = get_db()
    from datetime import timedelta
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    
    # Get all time logs in range
    logs = get_logs_for_range(user_id, start_iso, end_iso)
    logs_with_duration = compute_durations(logs)
    
    # Get all T/S logs in range
    ts_logs = get_ts_logs_for_range(user_id, start_iso, end_iso)
    ts_logs_with_duration = compute_ts_durations(ts_logs)
    
    # Calculate aggregates
    total_hours = sum(log['duration_hours'] for log in logs_with_duration)
    area_breakdown = aggregate_by_area(logs_with_duration)
    
    # Get active logs
    active_time_log = get_active_log(user_id)
    active_ts_log = get_active_ts_log(user_id)
    
    # Get task status breakdown
    task_by_status = {}
    for log in ts_logs:
        status = log['status'] or 'Pending'
        if status not in task_by_status:
            task_by_status[status] = 0
        task_by_status[status] += 1
    
    return {
        'total_hours': round(total_hours, 2),
        'area_breakdown': dict(area_breakdown),
        'active_time_log': active_time_log,
        'active_ts_log': active_ts_log,
        'task_count': len(ts_logs),
        'task_by_status': task_by_status,
        'time_logs': logs_with_duration,
        'ts_logs': ts_logs_with_duration,
    }


# Edit functionality functions

def update_time_log(log_id: int, user_id: int, area_id: int = None, start_time: str = None, end_time: str = None) -> bool:
    """Update a time log entry (only if owned by user and not active).
    
    Args:
        log_id: Time log ID to update.
        user_id: User ID (for ownership verification).
        area_id: New area ID (optional).
        start_time: New start time (ISO format, optional).
        end_time: New end time (ISO format, optional).
        
    Returns:
        True if update successful, False otherwise.
    """
    db = get_db()
    
    # Verify ownership and that log is not active
    log = db.execute(
        "SELECT * FROM time_log WHERE id = ? AND user_id = ? AND end_time IS NOT NULL",
        (log_id, user_id)
    ).fetchone()
    
    if not log:
        return False
    
    # Build update query
    updates = {}
    if area_id is not None:
        updates['area_id'] = area_id
    if start_time is not None:
        updates['start_time'] = start_time
    if end_time is not None:
        updates['end_time'] = end_time
    
    if not updates:
        return False
    
    updates['updated_at'] = datetime.utcnow().isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [log_id]
    query = f"UPDATE time_log SET {set_clause} WHERE id = ?"
    db.execute(query, values)
    db.commit()
    logger.info(f"Updated time log {log_id} for user {user_id}")
    return True


def update_ts_log(log_id: int, user_id: int, task_name: str = None, station: str = None, 
                  problem: str = None, solution: str = None, description: str = None, 
                  start_time: str = None, end_time: str = None, status: str = None, 
                  priority: str = None, category: str = None) -> bool:
    """Update a T/S log entry (only if owned by user and not active).
    
    Args:
        log_id: T/S log ID to update.
        user_id: User ID (for ownership verification).
        task_name: New task name (optional).
        station: New station (optional).
        problem: New problem description (optional).
        solution: New solution (optional).
        description: New description (optional).
        start_time: New start time (ISO format, optional).
        end_time: New end time (ISO format, optional).
        status: New status (optional).
        priority: New priority (optional).
        category: New category (optional).
        
    Returns:
        True if update successful, False otherwise.
    """
    db = get_db()
    
    # Verify ownership and that log is not active
    log = db.execute(
        "SELECT * FROM ts_log WHERE id = ? AND user_id = ? AND end_time IS NOT NULL",
        (log_id, user_id)
    ).fetchone()
    
    if not log:
        return False
    
    # Build update query
    updates = {}
    if task_name is not None:
        updates['task_name'] = task_name
    if station is not None:
        updates['station'] = station
    if problem is not None:
        updates['problem'] = problem
    if solution is not None:
        updates['solution'] = solution
    if description is not None:
        updates['description'] = description
    if start_time is not None:
        updates['start_time'] = start_time
    if end_time is not None:
        updates['end_time'] = end_time
    if status is not None:
        updates['status'] = status
    if priority is not None:
        updates['priority'] = priority
    if category is not None:
        updates['category'] = category
    
    if not updates:
        return False
    
    updates['updated_at'] = datetime.utcnow().isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [log_id]
    query = f"UPDATE ts_log SET {set_clause} WHERE id = ?"
    db.execute(query, values)
    db.commit()
    logger.info(f"Updated T/S log {log_id} for user {user_id}")
    return True


def get_time_log_by_id(log_id: int) -> Optional[sqlite3.Row]:
    """Get a specific time log entry by ID.
    
    Args:
        log_id: Time log ID to retrieve.
        
    Returns:
        Time log row if found, None otherwise.
    """
    db = get_db()
    cur = db.execute("SELECT * FROM time_log WHERE id = ?", (log_id,))
    return cur.fetchone()


# Export functionality functions

def get_export_data(user_id: int, start_date: str, end_date: str, data_type: str = 'both') -> Dict[str, Any]:
    """Get data for export in specified date range.
    
    Args:
        user_id: User ID to export data for.
        start_date: Start date (ISO format).
        end_date: End date (ISO format).
        data_type: 'time', 'ts', or 'both'.
        
    Returns:
        Dictionary with time_logs and/or ts_logs data.
    """
    result = {}
    
    if data_type in ['time', 'both']:
        logs = get_logs_for_range(user_id, start_date, end_date)
        result['time_logs'] = compute_durations(logs)
    
    if data_type in ['ts', 'both']:
        ts_logs = get_ts_logs_for_range(user_id, start_date, end_date)
        result['ts_logs'] = compute_ts_durations(ts_logs)
    
    return result
