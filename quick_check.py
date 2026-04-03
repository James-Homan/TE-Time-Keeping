from APP import create_app
import models

app = create_app()
with app.app_context():
    models.init_db()
    areas = models.get_areas()
    print('areas', len(areas))
    if areas:
        print('first', areas[0]['name'], areas[0]['charge_code_code'])
