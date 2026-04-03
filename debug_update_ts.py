#!/usr/bin/env python3
import APP
from models import start_ts_log, get_active_ts_log, update_ts_log_with_details, get_ts_log_by_id

app=APP.create_app()
with app.app_context():
    user_id=8
    start_ts_log(user_id,'debug task','desc','testing')
    active=get_active_ts_log(user_id)
    print('active before',active)
    update_ts_log_with_details(active['id'], station='Station A', problem='p', solution='s', status='In Progress', priority='High')
    log=get_ts_log_by_id(active['id'])
    print('log after',dict(log))
