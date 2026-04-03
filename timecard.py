"""Timecard module - displays summarized time allocation.

This module provides a timecard view that aggregates logged time by area
and displays it in a summary format with visualizations.
"""

import logging
from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for
from models import get_logs_for_range, compute_durations, aggregate_by_area
from area_logger import login_required

logger = logging.getLogger(__name__)
timecard_bp = Blueprint("timecard", __name__, url_prefix="/timecard")


@timecard_bp.route("/", methods=["GET"])
@login_required
def index():
    """Display timecard with aggregated time by area.
    
    Query Parameters:
        from: Start date (ISO format, defaults to today)
        to: End date (ISO format, defaults to start date)
    
    Returns:
        Rendered timecard template with time summary and chart data.
    """
    user_id = session["user_id"]
    start_date = request.args.get("from") or date.today().isoformat()
    end_date = request.args.get("to") or start_date

    try:
        logs = compute_durations(get_logs_for_range(user_id, start_date, end_date))
        summary = aggregate_by_area(logs)

        # Prepare data for Chart.js
        labels = []
        hours_data = []
        for (area_name, dept, charge), hours in summary.items():
            labels.append(f"{area_name} ({dept})")
            hours_data.append(round(hours, 3))

        if not labels:
            labels = ['No logged time']
            hours_data = [0]

        logger.debug(f"Generated timecard for user {user_id} from {start_date} to {end_date}")

        return render_template(
            "timecard.html",
            start_date=start_date,
            end_date=end_date,
            summary=summary,
            chart_labels=labels,
            chart_data=hours_data,
        )
    except Exception as e:
        logger.error(f"Error generating timecard: {e}")
        return redirect(url_for("dashboard"))
