# Made by Zachary Mangiafesto
from flask import Flask, render_template, session, redirect, url_for
from config import Config
from models import init_db, close_db
from auth import auth_bp
from area_logger import area_logger_bp
from timecard import timecard_bp
from ts_log import ts_log_bp
from management import management_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.before_request
    def _before_request():
        init_db()

    @app.teardown_appcontext
    def _teardown_db(exception):
        close_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(area_logger_bp)
    app.register_blueprint(timecard_bp)
    app.register_blueprint(ts_log_bp)
    app.register_blueprint(management_bp)

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response

    @app.route("/")
    def dashboard():
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return render_template("dashboard.html", username=session.get("username"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
