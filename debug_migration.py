#!/usr/bin/env python3

import APP
from models import init_db
from config import Config
import sqlite3

app = APP.create_app()
with app.app_context():
    init_db()
    conn = sqlite3.connect(Config.DATABASE)
    cur = conn.execute('PRAGMA table_info(ts_log)')
    print('ts_log columns:')
    for row in cur.fetchall():
        print(row)
    conn.close()
