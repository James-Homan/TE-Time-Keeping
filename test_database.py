from APP import create_app

app = create_app()

with app.app_context():
    from models import init_db, get_charge_codes, get_areas_with_charge_codes

    print("Initializing database...")
    init_db()
    print("Database initialized successfully")

    print("\nTesting charge codes:")
    charge_codes = get_charge_codes()
    print(f"Charge codes found: {len(charge_codes)}")
    for cc in charge_codes:
        print(f"  - {cc['code']}: {cc['description']} (Active: {cc['is_active']})")

    print("\nTesting areas:")
    areas = get_areas_with_charge_codes()
    print(f"Areas found: {len(areas)}")
    for area in areas:
        charge_code = area['charge_code_code'] or "No charge code"
        print(f"  - {area['name']}: {charge_code} (Active: {area['is_active']})")

    print("\nDatabase test completed successfully!")