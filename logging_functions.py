import streamlit as st
import datetime
from models import LogEntry
from utils import get_db, get_department_code
from config import IDLE

def start_logging():
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()

def start_logging_with_area(area: str = IDLE):
    st.session_state.logging_active = True
    st.session_state.entry_time = datetime.datetime.now()
    st.session_state.current_area = area

def stop_logging():
    if st.session_state.logging_active:
        now = datetime.datetime.now()
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.logging_active = False

def switch_area(new_area: str):
    now = datetime.datetime.now()
    if st.session_state.logging_active:
        log_entry_exit(st.session_state.current_area, st.session_state.entry_time, now)
        st.session_state.entry_time = now
    st.session_state.current_area = new_area

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
