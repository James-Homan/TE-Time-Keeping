from APP import create_app
import models

app = create_app()
with app.app_context():
    models.init_db()
    # create user if not exists
    user = models.get_user_by_username('testuser')
    if not user:
        models.create_user('testuser','testpass')
        user = models.get_user_by_username('testuser')
    user_id = user['id']

    models.start_ts_log(user_id, 'Test Task', 'ST123', 'Overheat', 'Restarted', 'Initial testing', 'Maintenance')
    active = models.get_active_ts_log(user_id)
    print('active', active['task_name'], active['station_fixture_id'])
    models.stop_ts_log(active['id'])
    logs = models.get_ts_logs_for_range(user_id, '2026-01-01', '2026-12-31')
    print('log count', len(logs), 'last', logs[-1]['task_name'], logs[-1]['problem_issues'], logs[-1]['solution'])
