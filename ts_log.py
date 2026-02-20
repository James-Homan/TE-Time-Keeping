from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import (
    get_active_ts_log,
    start_ts_log,
    stop_ts_log,
    get_ts_logs_for_range,
    compute_ts_durations,
)
from area_logger import login_required

ts_log_bp = Blueprint("ts_log", __name__, url_prefix="/ts-log")

@ts_log_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    user_id = session["user_id"]
    active_ts = get_active_ts_log(user_id)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "start":
            task_name = request.form.get("task_name", "").strip()
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()
            if not task_name:
                flash("Task name is required to start T/S log.", "error")
            else:
                if active_ts:
                    flash("You already have an active T/S log. Stop it before starting a new one.", "error")
                else:
                    start_ts_log(user_id, task_name, description, category)
            return redirect(url_for("ts_log.index"))

        if action == "stop":
            if active_ts:
                stop_ts_log(active_ts["id"])
            return redirect(url_for("ts_log.index"))

    # Date range filters for history
    start_date = request.args.get("from") or date.today().isoformat()
    end_date = request.args.get("to") or start_date

    raw_logs = get_ts_logs_for_range(user_id, start_date, end_date)
    logs = compute_ts_durations(raw_logs)

    return render_template(
        "ts_log.html",
        active_ts=active_ts,
        logs=logs,
        start_date=start_date,
        end_date=end_date,
    )
