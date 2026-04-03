import hashlib
import os

AREAS = {
    1: ("Vigilance Focus Factory", "60011"),
    2: ("Enterprise Focus Factory", "60015"),
    3: ("Liberty Focus Factory", "60012"),
    4: ("Intrepid Focus Factory", "60013"),
    5: ("Freedom Focus Factory", "60017"),
    6: ("Pioneer Focus Factory", "60014"),
    7: ("ESS Chambers", "ESS"),
    8: ("Breaks", "NPRD"),
    9: ("Training", "TRAIN"),
    10: ("E3 Projects", "NPRD")
}
IDLE = "Untracked (Idle)"

_charge_code_cache = {}

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return get_password_hash(plain) == hashed

def get_db():
    """Get database connection - placeholder for future use"""
    # This function is deprecated - use models.get_db() instead
    return None

def get_department_code(area_name: str) -> str:
    for _, (name, code) in AREAS.items():
        if name == area_name:
            return code
    return ""

def get_user_charge_code_by_username(username: str) -> str:
    """Deprecated: Get charge code for user by username
    
    This function is deprecated. Charge codes are now managed through
    the models.py interface with SQLite.
    """
    try:
        from models import get_db
        db = get_db()
        # Query the user and their metadata if needed
        user = db.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
        if user:
            # For now, return empty string - extend as needed
            return ""
    except Exception:
        pass
    return ""

def fetch_charge_code_for_user(username: str) -> str:
    if username in _charge_code_cache:
        return _charge_code_cache[username]

    code = ""
    try:
        db_code = get_user_charge_code_by_username(username)
        if db_code:
            _charge_code_cache[username] = db_code
            return db_code
    except Exception:
        pass

    if not code:
        code = os.environ.get("ORACLE_CHARGE_CODE") or os.environ.get("AGILE_CHARGE_CODE") or os.environ.get("BASELINE_CHARGE_CODE") or ""

    _charge_code_cache[username] = code
    return code

def set_user_charge_code_by_username(username: str, code: str) -> bool:
    """Deprecated: Set charge code for user
    
    This function is deprecated. Charge codes are now managed through
    the models.py interface with SQLite.
    """
    try:
        # Placeholder implementation for future enhancement
        # Would store user metadata in database
        return False
    except Exception:
        return False
