import sqlite3
import os

dbpath = os.path.join('instance', 'timecard.db')
try:
    db = sqlite3.connect(dbpath)
    cur = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"✓ Database is valid")
    print(f"✓ Tables found: {tables if tables else 'None (new DB)'}")
    db.close()
except Exception as e:
    print(f"✗ Error: {e}")
