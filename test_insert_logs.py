"""
Insert test log entries into the existing area_logger.db for user 'U136246'.
Creates the user if missing and inserts 20 varied entries across available areas.
"""
from sqlalchemy import create_engine, MetaData, Table, select
import datetime
import random
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'area_logger.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
metadata = MetaData()
metadata.reflect(bind=engine)

users = metadata.tables.get('users')
logs = metadata.tables.get('logs')

if users is None or logs is None:
    print('Database tables not found. Make sure APP.py has been run at least once to create the DB.')
    raise SystemExit(1)

conn = engine.connect()

username = 'U136246'
# Ensure user exists
res = conn.execute(select(users.c.id).where(users.c.username == username)).fetchone()
if res is None:
    print(f"User '{username}' not found. Creating user.")
    ins = users.insert().values(username=username, password_hash='', is_admin=False)
    r = conn.execute(ins)
    conn.commit()
    user_id = r.inserted_primary_key[0]
else:
    user_id = res[0]

print(f'Using user_id={user_id} for username={username}')

AREAS = [
    ("Vigilance Focus Factory", "60011"),
    ("Enterprise Focus Factory", "60015"),
    ("Liberty Focus Factory", "60012"),
    ("Intrepid Focus Factory", "60013"),
    ("Freedom Focus Factory", "60017"),
    ("Pioneer Focus Factory", "60014"),
    ("ESS Chambers", "ESS"),
    ("Breaks", "NPRD"),
    ("Training", "TRAIN"),
    ("E3 Projects", "NPRD"),
]

now = datetime.datetime.now()
entries = []
for i in range(20):
    days_ago = random.randint(0, 20)
    minute_offset = random.randint(0, 60*24-60)  # pick minute in the day
    entry_time = now - datetime.timedelta(days=days_ago, minutes=minute_offset)
    # choose duration between 5 minutes and 3 hours
    duration_minutes = random.randint(5, 180)
    exit_time = entry_time + datetime.timedelta(minutes=duration_minutes)
    area, dept = random.choice(AREAS)
    duration_seconds = (exit_time - entry_time).total_seconds()
    entries.append({
        'user_id': user_id,
        'area_name': area,
        'department_code': dept,
        'entry_time': entry_time,
        'exit_time': exit_time,
        'duration_seconds': duration_seconds,
    })

# Insert entries
for e in entries:
    conn.execute(logs.insert().values(**e))
conn.commit()

print(f'Inserted {len(entries)} log entries for {username}.')

# Print summary by area
from sqlalchemy import func
summary = conn.execute(select([logs.c.area_name, func.sum(logs.c.duration_seconds).label('total_seconds')]).where(logs.c.user_id==user_id).group_by(logs.c.area_name)).fetchall()
print('Summary (seconds) by area:')
for row in summary:
    area, secs = row
    hours = secs/3600.0 if secs else 0
    print(f' - {area}: {hours:.3f} hours')

conn.close()
