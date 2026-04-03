"""Authentication module for the TE Timekeeping application."""

import logging
import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import (
    create_user, 
    verify_user, 
    get_user_by_username,
    record_login_attempt,
    get_recent_failed_attempts,
    lock_user_account,
    is_user_locked,
    update_user_last_login,
    create_user_settings,
    get_active_log,
    stop_logging,
    get_active_ts_log,
    stop_ts_log,
    update_ts_log_with_details,
)

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

# Validation constants
MIN_PASSWORD_LENGTH = 8
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def is_valid_username(username: str) -> bool:
    """Validate username format.
    
    Args:
        username: Username to validate
        
    Returns:
        True if username is valid, False otherwise
    """
    if not username or len(username) < MIN_USERNAME_LENGTH or len(username) > MAX_USERNAME_LENGTH:
        return False
    # Allow alphanumeric, underscore, hyphen
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))


def is_valid_password(password: str) -> bool:
    """Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        True if password meets minimum requirements, False otherwise
    """
    return bool(password and len(password) >= MIN_PASSWORD_LENGTH)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with rate limiting."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required", "error")
            logger.warning(f"Login attempt with missing credentials from {request.remote_addr}")
            return render_template("login.html")

        try:
            # Get user (but don't fail if not found - prevents username enumeration)
            user = get_user_by_username(username)
            
            # Check if account is locked
            if user and is_user_locked(user["id"]):
                logger.warning(f"Login attempt on locked account: {username} from {request.remote_addr}")
                flash(
                    f"Account is locked due to too many failed login attempts. "
                    f"Please try again after {LOCKOUT_WINDOW_MINUTES} minutes.",
                    "error"
                )
                return render_template("login.html")
            
            # Check recent failed attempts
            if user:
                failed_attempts = get_recent_failed_attempts(user["id"], LOCKOUT_WINDOW_MINUTES)
                if failed_attempts >= MAX_FAILED_ATTEMPTS:
                    logger.warning(f"Max failed attempts reached for user {username}")
                    lock_user_account(user["id"])
                    flash(
                        f"Account locked after {MAX_FAILED_ATTEMPTS} failed attempts. "
                        f"Please try again after {LOCKOUT_WINDOW_MINUTES} minutes.",
                        "error"
                    )
                    return render_template("login.html")
            
            # Verify credentials
            verified_user = verify_user(username, password)
            if verified_user:
                # Successful login
                record_login_attempt(verified_user["id"], True, request.remote_addr)
                update_user_last_login(verified_user["id"])
                session["user_id"] = verified_user["id"]
                session["username"] = verified_user["username"]
                session.permanent = True
                logger.info(f"User {username} logged in successfully from {request.remote_addr}")
                return redirect(url_for("dashboard.index"))
            
            # Failed login - record attempt
            if user:
                record_login_attempt(user["id"], False, request.remote_addr)
                failed_attempts = get_recent_failed_attempts(user["id"], LOCKOUT_WINDOW_MINUTES)
                remaining_attempts = MAX_FAILED_ATTEMPTS - failed_attempts
                
                if remaining_attempts > 0:
                    logger.warning(f"Failed login for user {username} from {request.remote_addr}. "
                                 f"Attempts remaining: {remaining_attempts}")
                    flash(f"Invalid username or password. "
                          f"({remaining_attempts} attempt{'s' if remaining_attempts != 1 else ''} remaining)", 
                          "error")
                else:
                    lock_user_account(user["id"])
                    flash(
                        f"Account locked after {MAX_FAILED_ATTEMPTS} failed attempts. "
                        f"Please try again after {LOCKOUT_WINDOW_MINUTES} minutes.",
                        "error"
                    )
            else:
                # User not found - generic message to prevent enumeration
                logger.warning(f"Login attempt with non-existent username from {request.remote_addr}")
                flash("Invalid username or password", "error")
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash("An error occurred during login. Please try again.", "error")

    return render_template("login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle user signup."""
    if request.method == "POST":
        username = request.form.get("new_username", "").strip()
        password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Validation
        if not username:
            flash("Username is required", "error")
            return render_template("login.html")

        if not is_valid_username(username):
            flash(
                f"Username must be {MIN_USERNAME_LENGTH}-{MAX_USERNAME_LENGTH} characters "
                "and contain only letters, numbers, hyphens, and underscores",
                "error"
            )
            return render_template("login.html")

        if not password:
            flash("Password is required", "error")
            return render_template("login.html")

        if not is_valid_password(password):
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long", "error")
            return render_template("login.html")

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("login.html")

        if get_user_by_username(username):
            logger.warning(f"Signup attempt with existing username: {username}")
            flash("Username already exists", "error")
            return render_template("login.html")

        try:
            create_user(username, password)
            user = get_user_by_username(username)
            # Create default user settings
            if user:
                create_user_settings(user["id"])
            logger.info(f"New user created: {username}")
            flash("Account created successfully. You can now log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            flash("An error occurred while creating your account. Please try again.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Handle user logout and stop any active area or T/S timers."""
    user_id = session.get("user_id")
    username = session.get("username", "Unknown")

    if user_id:
        active_log = get_active_log(user_id)
        if active_log:
            try:
                stop_logging(active_log["id"])
                logger.info(f"Stopped active area log {active_log['id']} for user {user_id} on logout")
            except Exception as e:
                logger.error(f"Failed to stop active area log on logout for user {user_id}: {e}")

        active_ts_log = get_active_ts_log(user_id)
        if active_ts_log:
            try:
                update_ts_log_with_details(active_ts_log["id"], status="Completed")
                stop_ts_log(active_ts_log["id"])
                logger.info(f"Stopped active T/S log {active_ts_log['id']} for user {user_id} on logout")
            except Exception as e:
                logger.error(f"Failed to stop active T/S log on logout for user {user_id}: {e}")

    session.clear()
    logger.info(f"User {username} logged out")
    return redirect(url_for("auth.login"))
