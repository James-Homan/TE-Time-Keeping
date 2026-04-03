# Made by Zachary Mangiafesto
import os
import logging
from flask import Flask, render_template, session, redirect, url_for
from config import Config, DevelopmentConfig, ProductionConfig
from models import init_db, close_db
from auth import auth_bp
from area_logger import area_logger_bp
from timecard import timecard_bp
from ts_log import ts_log_bp
from management import management_bp
from dashboard import dashboard_bp
from settings import settings_bp


def create_app(config_class=None):
    """Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use. Defaults to DevelopmentConfig.
    
    Returns:
        Configured Flask application.
    """
    if config_class is None:
        env = os.environ.get("FLASK_ENV", "development")
        config_class = ProductionConfig if env == "production" else DevelopmentConfig
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize logging
    logger = config_class.init_logging()
    logger.info(f"Creating app with config: {config_class.__name__}")

    # Initialize database
    @app.before_request
    def _before_request():
        """Initialize DB on main process, not on reloader."""
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            try:
                init_db()
            except Exception as e:
                logger.error(f"Database initialization error: {e}")
                raise

    @app.teardown_appcontext
    def _teardown_db(exception):
        """Close database connection."""
        close_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(area_logger_bp)
    app.register_blueprint(timecard_bp)
    app.register_blueprint(ts_log_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(settings_bp)

    # Add security headers
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response

    # Dashboard route
    @app.route("/")
    def index():
        """Main dashboard - redirects to login if not authenticated."""
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return redirect(url_for("dashboard.index"))

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        logger.warning(f"404 error: {error}")
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"500 error: {error}")
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors."""
        logger.warning(f"403 error: {error}")
        return render_template('403.html'), 403

    logger.info("Application created successfully")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get('DEBUG', False))
