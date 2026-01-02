"""
Example agile_connector for local testing.
Implements get_charge_code(username) by reading connectors/agile_codes.csv if present.
CSV format: username,charge_code
"""
import csv
import os

def _load_map():
    path = os.path.join(os.path.dirname(__file__), "connectors", "agile_codes.csv")
    if not os.path.exists(path):
        return {}
    m = {}
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.reader(f)
        for row in r:
            if not row:
                continue
            user = row[0].strip()
            code = row[1].strip() if len(row) > 1 else ''
            m[user] = code
    return m

_CACHE = None

def get_charge_code(username: str) -> str:
    global _CACHE
    if _CACHE is None:
        _CACHE = _load_map()
    return _CACHE.get(username, "")
