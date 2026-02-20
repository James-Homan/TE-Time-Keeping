from datetime import date
import csv
from io import StringIO
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from models import (
    get_areas,
    get_active_log,
    start_logging,
    stop_logging,
    get_logs_for_range,
    compute_durations,
)

area_logger_bp = Blueprint("area_logger", __name__, url_prefix="/area-logger")

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapper

@area_logger_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    user_id = session["user_id"]
    areas = get_areas()
    active_log = get_active_log(user_id)

    if request.method == "POST":
        action = request.form.get("action")
        area_id = request.form.get("area_id")

        if action == "start":
            if active_log:
                flash("You already have an active log. Stop or switch first.", "error")
            elif area_id:
                start_logging(user_id, int(area_id))
            return redirect(url_for("area_logger.index"))

        if action == "stop":
            if active_log:
                stop_logging(active_log["id"])
            return redirect(url_for("area_logger.index"))

        if action == "switch":
            if active_log:
                stop_logging(active_log["id"])
            if area_id:
                start_logging(user_id, int(area_id))
            return redirect(url_for("area_logger.index"))

    # Date range filters
    start_date = request.args.get("from") or date.today().isoformat()
    end_date = request.args.get("to") or start_date

    raw_logs = get_logs_for_range(user_id, start_date, end_date)
    logs = compute_durations(raw_logs)

    return render_template(
        "area_logger.html",
        areas=areas,
        active_log=active_log,
        logs=logs,
        start_date=start_date,
        end_date=end_date,
    )

@area_logger_bp.route("/export")
@login_required
def export_csv():
    user_id = session["user_id"]
    start_date = request.args.get("from")
    end_date = request.args.get("to")
    if not start_date or not end_date:
        flash("From and To dates are required for export.", "error")
        return redirect(url_for("area_logger.index"))

    logs = compute_durations(get_logs_for_range(user_id, start_date, end_date))

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Area", "Department", "Charge Code", "Start Time", "End Time", "Duration (hours)"])
    for row in logs:
        writer.writerow([
            row["area_name"],
            row["department_code"],
            row["charge_code"],
            row["start_time"],
            row["end_time"] or "",
            f"{row['duration_hours']:.3f}",
        ])

    output = si.getvalue()
    filename = f"time_logs_{start_date}_to_{end_date}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
