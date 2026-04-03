import APP
from models import get_db
app = APP.create_app()
with app.app_context():
    conn = get_db()
    cols = conn.execute('PRAGMA table_info(user)').fetchall()
    colnames = [r[1] for r in cols]
    print('user cols', colnames)
    print('has last_login', 'last_login' in colnames)
