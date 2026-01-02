import streamlit as st
from sqlalchemy import create_engine, MetaData, Table, select, and_, func
import datetime
import os
import pandas as pd

st.set_page_config(page_title="TS Log", layout="wide")


# Safe rerun helper for compatibility across Streamlit versions
def _safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        try:
            from streamlit.runtime.scriptrunner.script_runner import RerunException
            raise RerunException()
        except Exception:
            st.stop()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'area_logger.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
metadata = MetaData()
metadata.reflect(bind=engine)

users = metadata.tables.get('users')
ts_logs = metadata.tables.get('ts_logs')

if ts_logs is None:
    st.error('TS logs table not found. Ensure APP.py has created the DB.')
    st.stop()

if 'user_id' not in st.session_state or st.session_state.get('user_id') is None:
    st.info('Please log in via the main app first.')
    st.stop()

user_id = st.session_state.user_id

st.title('Troubleshoot Log')

with st.expander('Create / Edit TS Entry'):
    col1, col2 = st.columns([2, 1])
    with col1:
        station = st.text_input('Station', key='ts_station')
        problem = st.text_area('Problem', key='ts_problem', height=120)
        solution = st.text_area('Solution', key='ts_solution', height=120)
    with col2:
        status = st.selectbox('Status', ['Pending', 'In Progress', 'Resolved'], index=0, key='ts_status')
        priority = st.selectbox('Priority', ['Low', 'Medium', 'High'], index=0, key='ts_priority')
        st.markdown('---')
        selected_id = st.selectbox('Select Entry to Edit', options=['New'] + [r[0] for r in engine.connect().execute(select(ts_logs.c.id).where(ts_logs.c.user_id == user_id)).fetchall()], key='ts_select')
        if selected_id != 'New':
            row = engine.connect().execute(select(ts_logs).where(ts_logs.c.id == selected_id)).fetchone()
            if row:
                station = st.session_state.ts_station = row['station']
                problem = st.session_state.ts_problem = row['problem']
                solution = st.session_state.ts_solution = row['solution']
                status = st.session_state.ts_status = row['status']
                priority = st.session_state.ts_priority = row['priority']
        save_cols = st.columns([1,1,1])
        if save_cols[0].button('Save'):
            conn = engine.connect()
            now = datetime.datetime.now()
            if selected_id == 'New':
                conn.execute(ts_logs.insert().values(user_id=user_id, station=st.session_state.ts_station, problem=st.session_state.ts_problem, solution=st.session_state.ts_solution, status=st.session_state.ts_status, priority=st.session_state.ts_priority, created_at=now))
                st.success('TS entry created')
            else:
                conn.execute(ts_logs.update().where(ts_logs.c.id == selected_id).values(station=st.session_state.ts_station, problem=st.session_state.ts_problem, solution=st.session_state.ts_solution, status=st.session_state.ts_status, priority=st.session_state.ts_priority))
                st.success('TS entry updated')
            conn.close()
            _safe_rerun()
        if save_cols[1].button('Delete') and selected_id != 'New':
            conn = engine.connect()
            conn.execute(ts_logs.delete().where(ts_logs.c.id == selected_id))
            conn.close()
            st.success('TS entry deleted')
            _safe_rerun()

st.markdown('---')

# Search and display
search_col1, search_col2 = st.columns([3,1])
with search_col1:
    q_text = st.text_input('Search (station/problem/solution)')
    start_date = st.date_input('From', value=datetime.date.today() - datetime.timedelta(days=21))
    end_date = st.date_input('To', value=datetime.date.today())
with search_col2:
    if st.button('Search'):
        pass

conn = engine.connect()
query = select(ts_logs).where(ts_logs.c.user_id == user_id)
if q_text:
    like = f"%{q_text}%"
    query = query.where((ts_logs.c.station.ilike(like)) | (ts_logs.c.problem.ilike(like)) | (ts_logs.c.solution.ilike(like)))
if start_date:
    query = query.where(ts_logs.c.created_at >= datetime.datetime.combine(start_date, datetime.time.min))
if end_date:
    query = query.where(ts_logs.c.created_at <= datetime.datetime.combine(end_date, datetime.time.max))
query = query.order_by(ts_logs.c.created_at.desc())
rows = conn.execute(query).fetchall()
conn.close()

if rows:
    df = pd.DataFrame(rows)
    # Show with columns
    st.dataframe(df[['id','created_at','station','status','priority','problem','solution']].rename(columns={'id':'ID','created_at':'Created'}))
else:
    st.info('No TS entries found for your query.')
