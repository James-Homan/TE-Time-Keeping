# Created By Zachary Mangiafesto & James Homan
from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for
from models import get_logs_for_range, compute_durations, aggregate_by_area
from area_logger import login_required

timecard_bp = Blueprint("timecard", __name__, url_prefix="/timecard")

@timecard_bp.route("/", methods=["GET"])
@login_required
def index():
    user_id = session["user_id"]
    start_date = request.args.get("from") or date.today().isoformat()
    end_date = request.args.get("to") or start_date

    logs = compute_durations(get_logs_for_range(user_id, start_date, end_date))
    summary = aggregate_by_area(logs)

    # Prepare data for Chart.js
    labels = []
    hours_data = []
    for (area_name, dept, charge), hours in summary.items():
        labels.append(f"{area_name} ({dept})")
        hours_data.append(round(hours, 3))

    return render_template(
        "timecard.html",
        start_date=start_date,
        end_date=end_date,
        summary=summary,
        chart_labels=labels,
        chart_data=hours_data,
    )
