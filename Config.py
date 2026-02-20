import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-me"
    DATABASE = os.path.join(BASE_DIR, "instance", "timecard.db")
    DEBUG = True

