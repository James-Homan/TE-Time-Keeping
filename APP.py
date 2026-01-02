# Made by Zachary Mangiafesto
import streamlit as st
import time
import hashlib
import datetime
from collections import defaultdict
import os

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, date2num
import importlib
_HAS_PLOTLY = False
try:
    import plotly.express as px
    _HAS_PLOTLY = True
except Exception:
    _HAS_PLOTLY = False
try:
    import docx
    _HAS_DOCX = True
except Exception:
    _HAS_DOCX = False

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Boolean, ForeignKey
)
from sqlalchemy import func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Area Logger", layout="wide")

# Dark mode default — controlled in sidebar below
_DARK_MODE_ENABLED = False

# Plugin detection: optional connectors
_oracle_connector = None
_agile_connector = None
_baseline_connector = None
try:
    _oracle_connector = importlib.import_module("oracle_connector")
except Exception:
    _oracle_connector = None
try:
    _agile_connector = importlib.import_module("agile_connector")
except Exception:
    _agile_connector = None
try:
    _baseline_connector = importlib.import_module("baseline_connector")
except Exception:
    _baseline_connector = None


# Compatibility shim: some Streamlit versions don't expose experimental_rerun
if not hasattr(st, "experimental_rerun"):
    def _compat_rerun():
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            st.stop()
    try:
        st.experimental_rerun = _compat_rerun
    except Exception:
        # best-effort: if assignment fails, ignore
        pass

# simple cache for fetched charge codes per username
_charge_code_cache = {}

def get_focus_factory(area_name: str) -> str:
    # Extract a short 'Focus Factory' label from the area name when possible
    if "Focus Factory" in area_name:
        return area_name
    # fallback: look for known tokens
    for token in ["Factory", "ESS", "Breaks", "Training", "Projects"]:
        if token in area_name:
            return token
    return area_name

def fetch_charge_code_for_user(username: str) -> str:
    # Return cached if available
    if username in _charge_code_cache:
        return _charge_code_cache[username]

    # Priority: connector modules (if installed) then environment variables
    code = ""
    # DB mapping has highest priority
    try:
        db_code = get_user_charge_code_by_username(username)
        if db_code:
            _charge_code_cache[username] = db_code
            return db_code
    except Exception:
        pass

    try:
        if _oracle_connector is not None and hasattr(_oracle_connector, "get_charge_code"):
            code = _oracle_connector.get_charge_code(username) or ""
    except Exception:
        code = ""

    if not code and _agile_connector is not None and hasattr(_agile_connector, "get_charge_code"):
        try:
            code = _agile_connector.get_charge_code(username) or ""
        except Exception:
            code = ""

    if not code and _baseline_connector is not None and hasattr(_baseline_connector, "get_charge_code"):
        try:
            code = _baseline_connector.get_charge_code(username) or ""
        except Exception:
            code = ""

    # Environment variable fallbacks (optional)
    if not code:
        code = os.environ.get("ORACLE_CHARGE_CODE") or os.environ.get("AGILE_CHARGE_CODE") or os.environ.get("BASELINE_CHARGE_CODE") or ""

    _charge_code_cache[username] = code
    return code

# --- Areas (same as your original) ---
AREAS = {
    1: ("Vigilance Focus Factory", "60011"),
    2: ("Enterprise Focus Factory", "60015"),
    3: ("Liberty Focus Factory", "60012"),
    4: ("Intrepid Focus Factory", "60013"),
    5: ("Freedom Focus Factory", "60017"),
    6: ("Pioneer Focus Factory", "60014"),
    7: ("ESS Chambers", "ESS"),
    8: ("Breaks", "NPRD"),
    9: ("Training", "TRAIN"),
    10: ("E3 Projects", "NPRD")
}
IDLE = "Untracked (Idle)"

# =============================
# DATABASE SETUP (SQLite local)
# =============================
Base = declarative_base()
engine = create_engine("sqlite:///area_logger.db")
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)

    logs = relationship("LogEntry", back_populates="user")

class LogEntry(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    area_name = Column(String, nullable=False)
    department_code = Column(String, nullable=True)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)

    user = relationship("User", back_populates="logs")

class UserMeta(Base):
    __tablename__ = "user_meta"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    charge_code = Column(String, nullable=True)

    user = relationship("User")

Base.metadata.create_all(bind=engine)

# Troubleshoot log table for TS entries
class TSLog(Base):
    __tablename__ = "ts_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    station = Column(String, nullable=True)
    problem = Column(String, nullable=True)
    solution = Column(String, nullable=True)
    status = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)

    user = relationship("User")

Base.metadata.create_all(bind=engine)

def insert_ts_log(user_id:int, station:str, problem:str, solution:str, status:str, priority:str):
    db = get_db()
    entry = TSLog(
        user_id=user_id,
        station=station,
        problem=problem,
        solution=solution,
        status=status,
        priority=priority,
        created_at=datetime.datetime.now()
    )
    db.add(entry)
    db.commit()
    return entry.id

def query_ts_logs(user_id:int=None, search: str=None, start: datetime.date=None, end: datetime.date=None):
    db = get_db()
    q = db.query(TSLog)
    if user_id is not None:
        q = q.filter(TSLog.user_id == user_id)
    if search:
        like = f"%{search}%"
        q = q.filter((TSLog.station.ilike(like)) | (TSLog.problem.ilike(like)) | (TSLog.solution.ilike(like)))
    if start:
        q = q.filter(TSLog.created_at >= datetime.datetime.combine(start, datetime.time.min))
    if end:
        q = q.filter(TSLog.created_at <= datetime.datetime.combine(end, datetime.time.max))
    rows = q.order_by(TSLog.created_at.desc()).all()
    return rows

# =============================
# UTILS
# =============================
def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return get_password_hash(plain) == hashed

def get_db():
    return SessionLocal()

def get_department_code(area_name: str) -> str:
    for _, (name, code) in AREAS.items():
        if name == area_name:
            return code
    return ""

def get_user_charge_code_by_username(username: str) -> str:
    # Check DB mapping first
    try:
        db = get_db()
        user = db.query(User).filter(User.username == username).first()
        if user:
            meta = db.query(UserMeta).filter(UserMeta.user_id == user.id).first()
            if meta and meta.charge_code:
                return meta.charge_code
    except Exception:
        pass
    return ""

def set_user_charge_code_by_username(username: str, code: str) -> bool:
    try:
        db = get_db()
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        meta = db.query(UserMeta).filter(UserMeta.user_id == user.id).first()
        if not meta:
            meta = UserMeta(user_id=user.id, charge_code=code)
            db.add(meta)
        else:
            meta.charge_code = code
        db.commit()
        return True
    except Exception:
        return False

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        # close the previous area and start timing the new one
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.entry_time = now
    # always update selected area but do not force a rerun — let Streamlit refresh naturally
    st.session_state.current_area = new_area

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    # do not call safe_rerun here; Streamlit will update after the button click

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    # let Streamlit refresh naturally

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        # let Streamlit refresh naturally

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)


def get_todays_logs(user_id: int) -> pd.DataFrame:
    db = get_db()
    today = datetime.date.today()
    start_dt = datetime.datetime.combine(today, datetime.time.min)
    end_dt = datetime.datetime.combine(today, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .order_by(LogEntry.entry_time.asc())
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "id": log.id,
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (hours)": round((log.duration_seconds or 0) / 3600.0, 4),
        })
    return pd.DataFrame(rows)


def get_totals_by_area_for_date(user_id: int, date: datetime.date) -> dict:
    db = get_db()
    start_dt = datetime.datetime.combine(date, datetime.time.min)
    end_dt = datetime.datetime.combine(date, datetime.time.max)
    q = db.query(LogEntry.area_name, func.sum(LogEntry.duration_seconds).label("secs"))
    q = q.filter(LogEntry.user_id == user_id).filter(LogEntry.entry_time >= start_dt).filter(LogEntry.entry_time <= end_dt)
    q = q.group_by(LogEntry.area_name)
    res = q.all()
    out = {r[0]: (r[1] or 0.0) / 3600.0 for r in res}
    return out


def get_totals_by_charge_code_for_date(user_id: int, date: datetime.date) -> dict:
    db = get_db()
    start_dt = datetime.datetime.combine(date, datetime.time.min)
    end_dt = datetime.datetime.combine(date, datetime.time.max)
    q = db.query(LogEntry.department_code, func.sum(LogEntry.duration_seconds).label("secs"))
    q = q.filter(LogEntry.user_id == user_id).filter(LogEntry.entry_time >= start_dt).filter(LogEntry.entry_time <= end_dt)
    q = q.group_by(LogEntry.department_code)
    res = q.all()
    out = {r[0] or "": (r[1] or 0.0) / 3600.0 for r in res}
    return out


def render_visuals(user_id: int, from_date: datetime.date, to_date: datetime.date, group_by: str = "Area", vis_type: str = "Pie"):
    """Render visualization for user's logs between dates.
    group_by: 'Area' or 'Department'
    vis_type: 'Pie', 'Bar', 'Timeline'
    """
    if not _HAS_PLOTLY:
        st.error("Plotly is not installed. Install it (e.g. `pip install plotly` or use `--trusted-host` if behind a proxy) to enable visuals.")
        return

    if user_id is None:
        st.info("Log in to view visualizations")
        return
    df = get_user_logs(user_id, from_date, to_date)
    if df.empty:
        st.info("No data for selected range")
        return

    # Ensure datetimes
    df = df.copy()
    df["Entry Time"] = pd.to_datetime(df["Entry Time"])
    df["Exit Time"] = pd.to_datetime(df["Exit Time"])

    if group_by not in ("Area", "Department"):
        group_by = "Area"

    if vis_type == "Pie":
        agg = df.groupby(group_by)["Duration (hours)"].sum().reset_index()
        fig = px.pie(agg, names=group_by, values="Duration (hours)", title=f"Time by {group_by}")
        st.plotly_chart(fig, use_container_width=True)
    elif vis_type == "Bar":
        agg = df.groupby(group_by)["Duration (hours)"].sum().reset_index()
        fig = px.bar(agg, x=group_by, y="Duration (hours)", title=f"Time by {group_by}", labels={"Duration (hours)":"Hours"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Timeline view: one bar per entry colored by group_by
        # Use plotly timeline
        try:
            df_t = df.copy()
            df_t["Start"] = df_t["Entry Time"]
            df_t["End"] = df_t["Exit Time"]
            # For readability, set y to Area (or Department)
            y_col = group_by
            fig = px.timeline(df_t, x_start="Start", x_end="End", y=y_col, color=group_by, hover_data=["Duration (hours)"])
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(title=f"Timeline ({group_by})")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Timeline visualization not available: {e}")

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    # Safety: only allow destructive admin reset when explicitly enabled
    if os.environ.get("ENABLE_RETEST_TOOLS") != "1":
        # not permitted in production; return False to indicate it didn't run
        return False
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        # close the previous area and start timing the new one
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.entry_time = now
    # update selected area but do not force a hard rerun; Streamlit will refresh
    st.session_state.current_area = new_area


def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    # let Streamlit redraw naturally


def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    # let Streamlit redraw naturally

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        # no explicit rerun; UI will update on button events

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    # Safety: only allow destructive admin reset when explicitly enabled
    if os.environ.get("ENABLE_RETEST_TOOLS") != "1":
        return False
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
    st.session_state.current_area = new_area
    st.session_state.entry_time = now
    safe_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    safe_rerun()

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    safe_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        # UI will update on button events; avoid forcing rerun

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    # Safety: only allow destructive admin reset when explicitly enabled
    if os.environ.get("ENABLE_RETEST_TOOLS") != "1":
        return False
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
    st.session_state.current_area = new_area
    st.session_state.entry_time = now
    safe_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    safe_rerun()

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    safe_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        safe_rerun()

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
    st.session_state.current_area = new_area
    st.session_state.entry_time = now
    safe_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    safe_rerun()

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    safe_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        safe_rerun()

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
    st.session_state.current_area = new_area
    st.session_state.entry_time = now
    safe_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    safe_rerun()

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    safe_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        safe_rerun()

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
    st.session_state.current_area = new_area
    st.session_state.entry_time = now
    safe_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    safe_rerun()

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    safe_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        safe_rerun()

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
    st.session_state.current_area = new_area
    st.session_state.entry_time = now
    safe_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    safe_rerun()

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    safe_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        safe_rerun()

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# SESSION STATE INIT
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_area" not in st.session_state:
    st.session_state.current_area = IDLE
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.datetime.now()
if "logging_active" not in st.session_state:
    st.session_state.logging_active = False
if "auto_start" not in st.session_state:
    st.session_state.auto_start = False
if "require_stop_confirm" not in st.session_state:
    st.session_state.require_stop_confirm = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "recent_limit" not in st.session_state:
    st.session_state.recent_limit = 20
if "app_page" not in st.session_state:
    st.session_state.app_page = "Area Logger"

# If an Oracle SSO-provided username is present in the environment, auto-login/create the user
oracle_user = os.environ.get("ORACLE_USER")
if oracle_user and st.session_state.user_id is None:
    db = get_db()
    existing = db.query(User).filter(User.username == oracle_user).first()
    if not existing:
        # create a local user record for the Oracle identity (no local password)
        u = User(username=oracle_user, password_hash=get_password_hash(""), is_admin=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        existing = u
    st.session_state.user_id = existing.id
    st.session_state.username = existing.username
    st.session_state.is_admin = existing.is_admin
    st.success(f"Signed in via Oracle as {existing.username}")

# =============================
# AUTH FUNCTIONS
# =============================
def signup(username: str, password: str, admin_code: str = ""):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        st.error("Username already exists.")
        return False

   

    is_admin = admin_code == "ADMIN123"  # simple shared admin code for demo
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        is_admin=is_admin
    )
    db.add(user)
    db.commit()
    st.success("Account created. You can now log in.")
    if is_admin:
        st.info("Registered as admin.")
    return True

def login(username: str, password: str):
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        st.error("Invalid username or password.")
        return False
    st.session_state.user_id = user.id
    st.session_state.username = user.username
    st.session_state.is_admin = user.is_admin
    st.success(f"Logged in as {user.username} ({'Admin' if user.is_admin else 'User'})")
    # Auto-start logging if user has enabled it in the sidebar
    if st.session_state.get("auto_start"):
        start_logging()
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

# Safe rerun helper to support multiple Streamlit versions
def safe_rerun():
    try:
        # Preferred API when available
        st.experimental_rerun()
    except AttributeError:
        # Fallback: try raising Streamlit's internal RerunException
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            # Final fallback: stop the script (user can refresh)
            st.stop()

# =============================
# LOGGING FUNCTIONS
# =============================
def log_entry_exit(area_name: str, entry_time: datetime.datetime, exit_time: datetime.datetime):
    if not st.session_state.logging_active:
        return
    if st.session_state.user_id is None:
        return

    db = get_db()
    duration = (exit_time - entry_time).total_seconds()
    code = get_department_code(area_name)

    log = LogEntry(
        user_id=st.session_state.user_id,
        area_name=area_name,
        department_code=code,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_seconds=duration
    )
    db.add(log)
    db.commit()

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
    st.session_state.current_area = new_area
    st.session_state.entry_time = now
    safe_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    safe_rerun()

def start_logging_with_area(area: str | None = None):
    # Start logging and set initial area; if no area provided, go to IDLE
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area if area else IDLE
    safe_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        safe_rerun()

# =============================
# DATA ACCESS / REPORT HELPERS
# =============================
def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.user_id == user_id)
        .filter(LogEntry.entry_time >= start_dt)
        .filter(LogEntry.entry_time <= end_dt)
        .all()
    )
    rows = []
    for log in logs:
        rows.append({
            "Area": log.area_name,
            "Department": log.department_code,
            "Entry Time": log.entry_time,
            "Exit Time": log.exit_time,
            "Duration (seconds)": log.duration_seconds,
            "Duration (hours)": log.duration_seconds / 3600.0
        })
    if not rows:
        return pd.DataFrame(columns=["Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])
    return pd.DataFrame(rows)

def delete_user_logs(user_id: int):
    db = get_db()
    try:
        db.query(LogEntry).filter(LogEntry.user_id == user_id).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

# New helper: clear logs for all users (admin "retest" action)
def clear_all_logs():
    try:
        db = get_db()
        # Delete all log entries, TS logs, and user meta mappings
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(TSLog).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False

# New helper: reset session state for quick retest
def reset_session_state():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.logging_active = False
    st.session_state.auto_start = False
    st.session_state.require_stop_confirm = False
    st.session_state.stop_requested = False
    st.session_state.recent_limit = 20
    st.session_state.app_page = "Area Logger"

# =============================
# RETEST ADMIN TOOLS (NEW)
# =============================
def create_test_admin(username: str = "testadmin", password: str = "test"):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    user = User(username=username, password_hash=get_password_hash(password), is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def run_retest_tools():
    st.sidebar.markdown("### Retest Tools")
    if st.sidebar.button("Clear all logs (admin)"):
        if clear_all_logs():
            st.sidebar.success("All logs, TS logs and user meta cleared.")
        else:
            st.sidebar.error("Failed to clear database.")
    if st.sidebar.button("Reset session state"):
        reset_session_state()
        st.sidebar.success("Session state reset.")
    if st.sidebar.button("Create test admin"):
        user = create_test_admin()
        st.sidebar.success(f"Test admin created: {user.username} (id={user.id})")
    if st.sidebar.button("Login as test admin"):
        db = get_db()
        user = db.query(User).filter(User.username == "testadmin").first()
        if not user:
            st.sidebar.error("testadmin not found — create it first.")
        else:
            st.session_state.user_id = user.id
            st.session_state.username = user.username
            st.session_state.is_admin = user.is_admin
            st.sidebar.success(f"Logged in as {user.username}")

# inject retest UI when the app loads — only if explicitly enabled via env var
try:
    if os.environ.get("ENABLE_RETEST_TOOLS") == "1":
        run_retest_tools()
except Exception:
    # non-fatal: avoid breaking the app if something goes wrong in tools
    pass


# -----------------------------
# External SSO detection + main UI
# -----------------------------
def _create_or_get_local_user(username: str) -> int:
    """Create a local DB user for an external identity if missing; return user id."""
    if not username:
        return None
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing.id
    u = User(username=username, password_hash=get_password_hash(""), is_admin=False)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u.id


def detect_external_user(preferred: str | None = None, allow_fallbacks: bool = False) -> bool:
    """Try to detect an externally-authenticated username from env vars or connector modules.
    If found, create a local user record (if missing) and sign them in. Returns True if a user was signed in.
    If `preferred` is provided it should be one of: 'oracle','agile','baseline' to prefer that provider.
    """
    providers = [
        ("oracle", _oracle_connector, "ORACLE_USER"),
        ("agile", _agile_connector, "AGILE_USER"),
        ("baseline", _baseline_connector, "BASELINE_USER"),
    ]

    order = providers
    if preferred:
        order = [p for p in providers if p[0] == preferred] + [p for p in providers if p[0] != preferred]

    import getpass
    tried = []
    errors = []

    # helper to attempt sign-in for a candidate username
    def _try_username(src_name: str, candidate: str, module=None):
        if not candidate:
            return False, f"no username from {src_name}"
        try:
            uid = _create_or_get_local_user(candidate)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = candidate
                # map charge code from connector if available
                try:
                    if module is not None and hasattr(module, "get_charge_code"):
                        code = module.get_charge_code(candidate) or ""
                        if code:
                            set_user_charge_code_by_username(candidate, code)
                except Exception:
                    pass
                return True, f"signed in via {src_name} as {candidate}"
        except Exception as e:
            return False, f"error creating local user from {src_name}: {e}"
        return False, f"failed to create local user from {src_name}"

    # Try provider-specific env vars / connector helpers first
    for name, module, envkey in order:
        tried.append(name)
        try:
            uname = os.environ.get(envkey)
        except Exception as e:
            uname = None
            errors.append(f"env lookup {envkey} failed: {e}")

        # connector-provided current user (optional)
        if not uname and module is not None and hasattr(module, "get_current_user"):
            try:
                uname = module.get_current_user()
            except Exception as e:
                errors.append(f"{name} connector.get_current_user() error: {e}")
                uname = None

        ok, msg = _try_username(name, uname, module)
        if ok:
            st.success(msg)
            return True
        else:
            errors.append(msg)

    # Try common OS username fallbacks only if explicitly allowed
    if allow_fallbacks:
        os_candidates = []
        try:
            os_candidates.append(os.environ.get("ORACLE_USER"))
        except Exception:
            pass
        try:
            os_candidates.append(os.environ.get("USERNAME"))
        except Exception:
            pass
        try:
            os_candidates.append(getpass.getuser())
        except Exception:
            pass
        try:
            os_candidates.append(os.getlogin())
        except Exception:
            pass

        for idx, cand in enumerate([c for c in os_candidates if c]):
            ok, msg = _try_username(f"os_fallback_{idx}", cand)
            if ok:
                st.success(msg)
                return True
            errors.append(msg)

        # As a last resort, try to probe connector CSVs for a likely username (non-invasive)
        try:
            base = os.path.join(os.path.dirname(__file__), "connectors")
            if os.path.isdir(base):
                for fn in os.listdir(base):
                    if fn.lower().endswith(".csv"):
                        try:
                            path = os.path.join(base, fn)
                            with open(path, encoding="utf-8") as f:
                                for line in f:
                                    parts = line.strip().split(",")
                                    if parts and parts[0]:
                                        candidate = parts[0].strip()
                                        ok, msg = _try_username(f"connector_csv:{fn}", candidate)
                                        if ok:
                                            st.success(msg)
                                            return True
                        except Exception:
                            continue
        except Exception:
            pass

    # nothing found
    # show a compact summary for the developer/user to help diagnose SSO problems
    summary = "Unable to auto-detect external user. Tried: " + ", ".join(tried)
    if errors:
        summary += ". Details: " + " | ".join(errors[:5])
    st.info(summary)
    return False


def _render_login_ui():
    st.title("Welcome — Sign in")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Login")
        lu = st.text_input("Username", key="login_username")
        lp = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in"):
            if login(lu, lp):
                safe_rerun()
    with col2:
        st.subheader("Create account")
        su = st.text_input("New username", key="signup_username")
        sp = st.text_input("New password", type="password", key="signup_password")
        sc = st.text_input("Admin code (optional)", key="signup_admin_code")
        if st.button("Sign up"):
            signup(su, sp, sc)

    st.markdown("---")
    st.info("Automatic detection: if you're signed into Oracle/Agile/Baseline on this machine, click detect.")
    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button("Detect Oracle SSO"):
            if detect_external_user(preferred="oracle"):
                safe_rerun()
            else:
                st.warning("No Oracle user detected (env ORACLE_USER or connector.get_current_user()).")
    with s2:
        if st.button("Detect Agile SSO"):
            if detect_external_user(preferred="agile"):
                safe_rerun()
            else:
                st.warning("No Agile user detected (env AGILE_USER or connector.get_current_user()).")
    with s3:
        if st.button("Detect Baseline SSO"):
            if detect_external_user(preferred="baseline"):
                safe_rerun()
            else:
                st.warning("No Baseline user detected (env BASELINE_USER or connector.get_current_user()).")

    if st.button("Detect All SSO"):
        if detect_external_user():
            safe_rerun()
        else:
            st.warning("No external SSO could be detected. See the info message for details.")


def _render_area_logger_ui():
    st.title("Area Logger")
    # style area buttons to look more like the Tkinter layout (bigger, multiline)
    st.markdown(
        """
        <style>
        .stButton>button {
            height: 64px;
            width: 100%;
            white-space: pre-wrap;
            font-size: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"**Signed in as:** {st.session_state.username}")
    st.markdown("---")

    # Top row: Controls | Current Status | My Dashboard
    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        st.subheader("Controls")
        if st.session_state.logging_active:
            st.warning("Confirm stopping logging")
            stop_cols = st.columns([1,1])
            if stop_cols[0].button("Confirm Stop"):
                stop_logging()
            if stop_cols[1].button("Cancel"):
                st.info("Stop cancelled")
        else:
            if st.button("Start logging"):
                start_logging()
        if st.button("Set to Idle"):
            switch_area(IDLE)
        st.markdown("---")
        st.checkbox("Require confirmation to stop logging", key="require_stop_confirm")

    with c2:
        st.subheader("Current Status")
        st.markdown("**Selected Area**")
        cur_area = st.session_state.current_area or IDLE
        dept = get_department_code(cur_area)
        st.markdown(f"### {cur_area}")
        st.write("Department code:", dept or "(none)")
        # show linked charge code for current user
        if st.session_state.username:
            cc = fetch_charge_code_for_user(st.session_state.username)
            st.write("Charge code:", cc or "(not set)")

        st.markdown("**Timer Status**")
        active = st.session_state.logging_active
        st.write("Logging Active:", "Yes" if active else "No")
        if active and st.session_state.current_area == cur_area:
            elapsed = datetime.datetime.now() - st.session_state.entry_time
            st.success(f"Time in Current Area: {str(elapsed).split('.')[0]}")
            stop_col = st.columns([1,1])
            if stop_col[0].button("Stop Logging", key="stop_now"):
                stop_logging()
            if stop_col[1].button("Refresh Timer", key="refresh_timer"):
                safe_rerun()
        else:
            if st.button("Start Logging in this area", key="start_here"):
                # start and set current area
                start_logging_with_area(cur_area)

    with c3:
        st.subheader("Switch Area")
        # show the full area grid here so all areas are immediately selectable
        area_items = list(AREAS.values())
        area_totals = get_totals_by_area_for_date(st.session_state.user_id, datetime.date.today()) if st.session_state.user_id else {}
        # use 3 columns across to match the intended layout and avoid
        # earlier columns collapsing when selecting an area
        n_cols = 3
        # Create fixed top-level columns and stack area items vertically in each
        cols = st.columns(n_cols)
        for idx, (name, code) in enumerate(area_items):
            target_col = cols[idx % n_cols]
            hours = area_totals.get(name, 0.0)
            label = f"{name}\n({code})\n{hours:.2f}h"
            # for each stacked entry create a small indicator + button pair
            left, right = target_col.columns([1, 9])
            is_active = st.session_state.get("current_area") == name
            color = "#2E8B57"
            if is_active:
                left.markdown(
                    f"""
                    <div style="width:100%;height:56px;border-left:6px solid {color};border-radius:4px;margin-top:6px;"></div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                left.markdown("<div style='width:100%;height:56px;margin-top:6px;'></div>", unsafe_allow_html=True)

            if right.button(label, key=f"area_top_full_{idx}"):
                switch_area(name)

    # Second row: Switch Area (left) | Recent Activity (right)
    left, right = st.columns([2,4])
    with left:
        st.subheader("My Dashboard")
        from_date = st.date_input("From", value=datetime.date.today() - datetime.timedelta(days=14), key="dash_from")
        to_date = st.date_input("To", value=datetime.date.today(), key="dash_to")
        if st.button("Refresh Dashboard"):
            safe_rerun()
        # Visualization controls
        vis_group = st.selectbox("Group by", ["Area", "Department"], index=0, key="vis_group")
        vis_type = st.selectbox("Chart type", ["Pie","Bar","Timeline"], index=0, key="vis_type")
        if st.button("Render visualization"):
            try:
                render_visuals(st.session_state.user_id, from_date, to_date, vis_group, vis_type)
            except Exception as e:
                st.error(f"Failed to render visualization: {e}")

    with right:
        st.subheader("Recent Activity")
        if st.session_state.user_id is None:
            st.info("Log in to see activity")
        else:
            df = get_user_logs(st.session_state.user_id, from_date, to_date)
            if df.empty:
                st.info("No activity for selected range")
            else:
                st.dataframe(df)
                if st.button("Export range to CSV"):
                    try:
                        from helpers.exporter import df_to_csv_bytes
                        b = df_to_csv_bytes(df)
                        st.download_button("Download CSV", data=b, file_name=f"logs_{st.session_state.username}_{from_date}_{to_date}.csv", mime="text/csv")
                    except Exception as e:
                        st.error(f"Export failed: {e}")




def _render_timecard_ui():
    st.title("Timecard")
    st.markdown(f"**Signed in as:** {st.session_state.username}")
    code = fetch_charge_code_for_user(st.session_state.username or "")
    st.write("Detected charge code:", code or "(none)")
    new_code = st.text_input("Set department/charge code for your account", value=code or "", key="timecard_set_code")
    if st.button("Save charge code"):
        if set_user_charge_code_by_username(st.session_state.username, new_code):
            st.success("Charge code saved")
        else:
            st.error("Failed to save charge code")
    st.markdown("---")
    st.write("Use the Area Logger or TS Log pages for further actions.")
    # If an external Tkinter timecard exists, offer to launch it externally
    import subprocess, sys
    if os.path.exists(os.path.join(os.path.dirname(__file__), "TESTENG_Timecard.py")):
        if st.button("Launch external Timecard (TESTENG_Timecard.py)"):
            try:
                subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "TESTENG_Timecard.py")])
                st.info("Launched external timecard process.")
            except Exception as e:
                st.error(f"Failed to launch: {e}")


# Top-level navigation/render
try:
    if st.session_state.get("user_id") is None:
        _render_login_ui()
    else:
        # logged in: show sidebar navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.selectbox("Select page", ["Area Logger", "Timecard", "TS Log"], index=0)
        st.sidebar.markdown("---")
        if st.sidebar.button("Log out"):
            logout()
            safe_rerun()

        if page == "TS Log":
            # Attempt to run the Streamlit TS_Log page as a module
            try:
                importlib.import_module("pages.TS_Log")
            except Exception as e:
                st.error(f"Failed to load TS Log page: {e}")
        elif page == "Timecard":
            _render_timecard_ui()
        else:
            _render_area_logger_ui()
except Exception:
    # top-level UI should not crash the app
    pass
