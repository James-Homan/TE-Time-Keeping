from sqlalchemy import create_engine, MetaData, Table, select, func
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'area_logger.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
metadata = MetaData()
metadata.reflect(bind=engine)

users = metadata.tables.get('users')
logs = metadata.tables.get('logs')

conn = engine.connect()
username = 'U136246'
res = conn.execute(select(users.c.id).where(users.c.username==username)).fetchone()
if res is None:
    print('User not found')
    raise SystemExit(1)
user_id = res[0]

summary = conn.execute(select(logs.c.area_name, func.sum(logs.c.duration_seconds).label('total_seconds')).where(logs.c.user_id==user_id).group_by(logs.c.area_name)).fetchall()
print('Summary (hours) by area for', username)
for area, secs in summary:
    hours = (secs or 0)/3600.0
    print(f'- {area}: {hours:.3f} hours')

count = conn.execute(select(func.count()).select_from(logs).where(logs.c.user_id==user_id)).scalar()
print('Total log rows for user:', count)
conn.close()
