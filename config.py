import os
import logging

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class for the application."""
    
    # Flask config
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-change-me-in-production"
    DATABASE = os.path.join(BASE_DIR, "instance", "timecard.db")
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    TESTING = False
    
    # Security
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Logging
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    
    @staticmethod
    def init_logging():
        """Initialize logging configuration."""
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        
        log_file = os.path.join(Config.LOG_DIR, "app.log")
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    DATABASE = ":memory:"

