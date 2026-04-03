import APP
from models import init_db, get_db

app = APP.create_app()
with app.app_context():
    init_db()
    conn = get_db()
    cols = [r[1] for r in conn.execute('PRAGMA table_info(user)').fetchall()]
    print('after init_db user cols', cols)
    print('last_login:', 'last_login' in cols)
