from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import create_user, verify_user, get_user_by_username

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = verify_user(username, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "error")

    return render_template("login.html")

@auth_bp.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("new_username", "").strip()
    password = request.form.get("new_password", "").strip()

    if not username or not password:
        flash("Username and password are required", "error")
        return redirect(url_for("auth.login"))

    if get_user_by_username(username):
        flash("Username already exists", "error")
        return redirect(url_for("auth.login"))

    create_user(username, password)
    flash("Account created. You can now log in.", "success")
    return redirect(url_for("auth.login"))

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
