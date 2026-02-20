import pandas as pd
import datetime
from utils import get_db
from models import LogEntry
from sqlalchemy import func
import plotly.express as px
import streamlit as st

def get_user_logs(user_id: int, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    db = get_db()
    start_dt = datetime.datetime.combine(start, datetime.time.min)
    end_dt = datetime.datetime.combine(end, datetime.time.max)
    logs = db.query(LogEntry)\
             .filter(LogEntry.user_id == user_id)\
             .filter(LogEntry.entry_time >= start_dt)\
             .filter(LogEntry.entry_time <= end_dt)\
             .all()
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

def render_visuals(user_id: int, from_date: datetime.date, to_date: datetime.date, group_by: str = "Area", vis_type: str = "Pie"):
    if user_id is None:
        st.info("Log in to view visualizations")
        return
    df = get_user_logs(user_id, from_date, to_date)
    if df.empty:
        st.info("No data for selected range")
        return

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
        fig = px.bar(agg, x=group_by, y="Duration (hours)", title=f"Time by {group_by}", labels={"Duration (hours)": "Hours"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        df_t = df.copy()
        df_t["Start"] = df_t["Entry Time"]
        df_t["End"] = df_t["Exit Time"]
        y_col = group_by
        fig = px.timeline(df_t, x_start="Start", x_end="End", y=y_col, color=group_by, hover_data=["Duration (hours)"])
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(title=f"Timeline ({group_by})")
        st.plotly_chart(fig, use_container_width=True)

def clear_all_logs():
    try:
        db = get_db()
        db.query(LogEntry).delete(synchronize_session=False)
        db.query(UserMeta).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
