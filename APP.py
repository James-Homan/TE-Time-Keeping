import streamlit as st
import time
import hashlib
import datetime
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, date2num

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Area Logger", layout="wide")

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

Base.metadata.create_all(bind=engine)

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
    return True

def logout():
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False
    st.session_state.current_area = IDLE
    st.session_state.logging_active = False

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
    st.experimental_rerun()

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.experimental_rerun()

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False
        st.experimental_rerun()

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

def get_all_users() -> pd.DataFrame:
    db = get_db()
    users = db.query(User).all()
    data = [{
        "id": u.id,
        "username": u.username,
        "is_admin": u.is_admin
    } for u in users]
    return pd.DataFrame(data)

# =============================
# CHARTS
# =============================
def plot_pie_time_per_area(df: pd.DataFrame):
    if df.empty:
        st.info("No data for this range.")
        return
    summary = df.groupby("Area")["Duration (hours)"].sum()
    fig, ax = plt.subplots()
    ax.pie(summary.values, labels=summary.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Time Distribution by Area")
    st.pyplot(fig)

def plot_daily_bar(df: pd.DataFrame):
    if df.empty:
        st.info("No data for this range.")
        return
    df["Date"] = df["Entry Time"].dt.date
    summary = df.groupby(["Date", "Area"])["Duration (hours)"].sum().reset_index()

    dates = sorted(summary["Date"].unique())
    areas = sorted(summary["Area"].unique())

    fig, ax = plt.subplots(figsize=(10, 5))
    bar_width = 0.8 / max(len(areas), 1)
    date_pos = {d: i for i, d in enumerate(dates)}

    for i, area in enumerate(areas):
        subset = summary[summary["Area"] == area]
        xs = [date_pos[d] + i * bar_width for d in subset["Date"]]
        ys = subset["Duration (hours)"]
        ax.bar(xs, ys, width=bar_width, label=area)

    ax.set_xticks([date_pos[d] + bar_width * (len(areas) / 2) for d in dates])
    ax.set_xticklabels(dates, rotation=45)
    ax.set_ylabel("Hours")
    ax.set_title("Daily Time per Area")
    ax.legend()
    st.pyplot(fig)

def plot_gantt(df: pd.DataFrame):
    if df.empty:
        st.info("No data for this range.")
        return

    df = df.sort_values("Entry Time")
    df["StartNum"] = df["Entry Time"].map(date2num)
    df["EndNum"] = df["Exit Time"].map(date2num)
    df["Duration"] = df["EndNum"] - df["StartNum"]

    areas = list(df["Area"].unique())
    area_pos = {area: i for i, area in enumerate(areas)}

    fig, ax = plt.subplots(figsize=(12, 6))
    for _, row in df.iterrows():
        y = area_pos[row["Area"]]
        ax.barh(y, row["Duration"], left=row["StartNum"])

    ax.set_yticks(list(area_pos.values()))
    ax.set_yticklabels(areas)
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d\n%H:%M"))
    ax.set_xlabel("Time")
    ax.set_title("Gantt View of Activity")
    st.pyplot(fig)

# =============================
# UI LAYOUT
# =============================
st.title("Area Logger – Streamlit Platform")

# --- Auth sidebar ---
with st.sidebar:
    st.header("Authentication")

    if st.session_state.user_id is None:
        tabs = st.tabs(["Login", "Sign up"])

        with tabs[0]:
            login_user = st.text_input("Username", key="login_user")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                if login_user and login_pass:
                    login(login_user, login_pass)
        with tabs[1]:
            new_user = st.text_input("New Username", key="new_user")
            new_pass = st.text_input("New Password", type="password", key="new_pass")
            admin_code = st.text_input("Admin Code (optional)", type="password", help="Enter special admin code if you should be admin.")
            if st.button("Create Account"):
                if new_user and new_pass:
                    signup(new_user, new_pass, admin_code)
    else:
        st.write(f"**Logged in as:** {st.session_state.username}")
        st.write(f"**Role:** {'Admin' if st.session_state.is_admin else 'User'}")
        if st.button("Logout"):
            logout()
            st.experimental_rerun()

# If not logged in, stop here
if st.session_state.user_id is None:
    st.info("Please log in or sign up to use the app.")
    st.stop()

# --- Main tabs: User vs Admin ---
main_tabs = st.tabs(["My Tracking", "Admin Dashboard" if st.session_state.is_admin else ""])

# =============================
# TAB 1: USER TRACKING
# =============================
with main_tabs[0]:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Controls")

        if not st.session_state.logging_active:
            if st.button("Start Logging", use_container_width=True):
                start_logging()
        else:
            if st.button("Stop Logging", use_container_width=True):
                stop_logging()

        if st.button("Set to Idle", use_container_width=True):
            switch_area(IDLE)

        st.markdown("---")
        st.subheader("Switch Area")
        for _, (name, code) in AREAS.items():
            if st.button(f"{name} ({code})"):
                switch_area(name)

    with col2:
        st.subheader("Current Status")
        now = datetime.datetime.now()
        elapsed_sec = (now - st.session_state.entry_time).total_seconds()
        st.write(f"**Current Area:** {st.session_state.current_area}")
        st.write(f"**Logging Active:** {st.session_state.logging_active}")
        st.write(f"**Time in Current Area:** {round(elapsed_sec, 1)} seconds")

        st.button("Refresh Timer")

        st.markdown("---")
        st.subheader("My Dashboard")

        start_date = st.date_input("From", datetime.date.today() - datetime.timedelta(days=7), key="user_from")
        end_date = st.date_input("To", datetime.date.today(), key="user_to")

        df_user = get_user_logs(st.session_state.user_id, start_date, end_date)

        st.write("Raw data:")
        st.dataframe(df_user)

        st.markdown("### Pie Chart – Time per Area")
        plot_pie_time_per_area(df_user)

        st.markdown("### Bar Chart – Daily Time per Area")
        plot_daily_bar(df_user)

        st.markdown("### Gantt View")
        plot_gantt(df_user)

        # Export to Excel for user
        if not df_user.empty:
            excel_bytes = df_user.to_excel(index=False, engine="openpyxl")
            # Workaround: use a BytesIO buffer to export properly
            from io import BytesIO
            buffer = BytesIO()
            df_user.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="Download my data as Excel",
                data=buffer,
                file_name=f"{st.session_state.username}_logs_{start_date}_to_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# =============================
# TAB 2: ADMIN DASHBOARD
# =============================
if st.session_state.is_admin and len(main_tabs) > 1:
    with main_tabs[1]:
        st.header("Admin Dashboard")

        users_df = get_all_users()
        st.subheader("Users")
        st.dataframe(users_df)

        if users_df.empty:
            st.info("No users yet.")
        else:
            user_map = dict(zip(users_df["username"], users_df["id"]))
            selected_user = st.selectbox("Select user", options=["All"] + list(user_map.keys()))

            start_date_a = st.date_input("From", datetime.date.today() - datetime.timedelta(days=7), key="admin_from")
            end_date_a = st.date_input("To", datetime.date.today(), key="admin_to")

            db = get_db()
            start_dt = datetime.datetime.combine(start_date_a, datetime.time.min)
            end_dt = datetime.datetime.combine(end_date_a, datetime.time.max)

            q = db.query(LogEntry, User.username).join(User, LogEntry.user_id == User.id)
            q = q.filter(LogEntry.entry_time >= start_dt, LogEntry.entry_time <= end_dt)

            if selected_user != "All":
                q = q.filter(User.username == selected_user)

            results = q.all()

            rows = []
            for log, username in results:
                rows.append({
                    "Username": username,
                    "Area": log.area_name,
                    "Department": log.department_code,
                    "Entry Time": log.entry_time,
                    "Exit Time": log.exit_time,
                    "Duration (seconds)": log.duration_seconds,
                    "Duration (hours)": log.duration_seconds / 3600.0
                })

            if rows:
                df_admin = pd.DataFrame(rows)
            else:
                df_admin = pd.DataFrame(columns=["Username", "Area", "Department", "Entry Time", "Exit Time", "Duration (seconds)", "Duration (hours)"])

            st.subheader("Logs")
            st.dataframe(df_admin)

            # Weekly summary (automatic style)
            st.subheader("Weekly Summary (Hours per User per Area)")
            if not df_admin.empty:
                df_admin["Week"] = df_admin["Entry Time"].dt.to_period("W").apply(lambda r: r.start_time.date())
                summary = df_admin.groupby(["Week", "Username", "Area"])["Duration (hours)"].sum().reset_index()
                st.dataframe(summary)

            # Export all data to Excel
            if not df_admin.empty:
                from io import BytesIO
                buffer = BytesIO()
                df_admin.to_excel(buffer, index=False)
                buffer.seek(0)
                st.download_button(
                    label="Download filtered logs as Excel",
                    data=buffer,
                    file_name=f"logs_{selected_user}_{start_date_a}_to_{end_date_a}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
