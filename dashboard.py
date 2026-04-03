"""Dashboard module - comprehensive metrics and status overview.

This module provides dashboard views that display real-time status, 
comprehensive metrics, time summaries, and productivity analytics 
for users to monitor their timekeeping.
"""

import logging
from datetime import date, timedelta
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from models import (
    get_dashboard_summary,
    get_logs_for_range,
    get_ts_logs_for_range,
    compute_durations,
    compute_ts_durations,
    aggregate_by_area,
    get_active_log,
    get_active_ts_log,
)
from area_logger import login_required

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/", methods=["GET"])
@login_required
def index():
    """Display comprehensive dashboard with current status and metrics.
    
    Returns:
        Rendered dashboard template with metrics, active logs, and visualizations.
    """
    user_id = session["user_id"]
    
    try:
        # Get summary data (default: current day)
        summary = get_dashboard_summary(user_id, days_back=1)
        
        # Get current date
        today = date.today().isoformat()
        
        # Get week summary
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        week_end = date.today().isoformat()
        week_logs = get_logs_for_range(user_id, week_start, week_end)
        week_durations = compute_durations(week_logs)
        week_hours = sum(log['duration_hours'] for log in week_durations)
        
        # Get month summary
        month_start = date.today().replace(day=1).isoformat()
        month_end = date.today().isoformat()
        month_logs = get_logs_for_range(user_id, month_start, month_end)
        month_durations = compute_durations(month_logs)
        month_hours = sum(log['duration_hours'] for log in month_durations)
        
        # Format area breakdown for charts
        labels = []
        hours_data = []
        for (area_name, dept, charge), hours in summary['area_breakdown'].items():
            labels.append(f"{area_name}")
            hours_data.append(round(hours, 2))

        if not labels:
            labels = ['No logged time']
            hours_data = [0]
        
        # Format task status breakdown
        status_labels = list(summary['task_by_status'].keys()) if summary['task_by_status'] else ['No Tasks']
        status_data = list(summary['task_by_status'].values()) if summary['task_by_status'] else [0]
        
        logger.debug(f"Generated dashboard for user {user_id}")
        
        return render_template(
            "dashboard.html",
            today=today,
            total_hours=summary['total_hours'],
            active_time_log=summary['active_time_log'],
            active_ts_log=summary['active_ts_log'],
            area_breakdown=summary['area_breakdown'],
            task_count=summary['task_count'],
            task_by_status=summary['task_by_status'],
            chart_labels=labels,
            chart_data=hours_data,
            status_labels=status_labels,
            status_data=status_data,
            week_hours=round(week_hours, 2),
            month_hours=round(month_hours, 2),
            recent_logs=summary['time_logs'][-10:] if summary['time_logs'] else [],
            recent_tasks=summary['ts_logs'][-10:] if summary['ts_logs'] else [],
        )
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        return render_template("dashboard.html", error=str(e))


@dashboard_bp.route("/api/summary", methods=["GET"])
@login_required
def api_summary():
    """API endpoint for dashboard summary data (for AJAX updates).
    
    Query Parameters:
        days: Number of days to look back (default 1)
    
    Returns:
        JSON with dashboard metrics and summary data.
    """
    user_id = session["user_id"]
    days_back = request.args.get("days", default=1, type=int)
    
    try:
        summary = get_dashboard_summary(user_id, days_back=days_back)
        
        return jsonify({
            'status': 'success',
            'total_hours': summary['total_hours'],
            'active_time_log': dict(summary['active_time_log']) if summary['active_time_log'] else None,
            'active_ts_log': dict(summary['active_ts_log']) if summary['active_ts_log'] else None,
            'task_count': summary['task_count'],
            'task_by_status': summary['task_by_status'],
            'area_breakdown': {str(k): v for k, v in summary['area_breakdown'].items()},
        })
    except Exception as e:
        logger.error(f"Error generating API summary: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@dashboard_bp.route("/detailed", methods=["GET"])
@login_required
def detailed():
    """Display detailed dashboard with extended date range and analytics.
    
    Query Parameters:
        from: Start date (ISO format, defaults to 30 days ago)
        to: End date (ISO format, defaults to today)
    
    Returns:
        Rendered detailed dashboard template with analytics and trends.
    """
    user_id = session["user_id"]
    today = date.today()
    thirty_days_ago = (today - timedelta(days=30)).isoformat()
    
    start_date = request.args.get("from") or thirty_days_ago
    end_date = request.args.get("to") or today.isoformat()
    
    try:
        # Get logs and compute durations
        logs = get_logs_for_range(user_id, start_date, end_date)
        logs_with_duration = compute_durations(logs)
        
        # Get T/S logs
        ts_logs = get_ts_logs_for_range(user_id, start_date, end_date)
        ts_durations = compute_ts_durations(ts_logs)
        
        # Calculate aggregates
        total_hours = sum(log['duration_hours'] for log in logs_with_duration)
        area_breakdown = aggregate_by_area(logs_with_duration)
        
        # Calculate daily breakdown
        daily_summary = {}
        for log in logs_with_duration:
            day = log['start_time'][:10]  # ISO date
            if day not in daily_summary:
                daily_summary[day] = 0.0
            daily_summary[day] += log['duration_hours']
        
        # Sort daily summary
        sorted_days = sorted(daily_summary.items())
        daily_labels = [day for day, _ in sorted_days]
        daily_hours = [round(hours, 2) for _, hours in sorted_days]
        
        # Format area breakdown for charts
        area_labels = []
        area_hours = []
        for (area_name, dept, charge), hours in area_breakdown.items():
            area_labels.append(f"{area_name}")
            area_hours.append(round(hours, 2))
        
        # Task analytics
        task_by_priority = {}
        for task in ts_logs:
            priority = task['priority'] or 'Low'
            if priority not in task_by_priority:
                task_by_priority[priority] = 0
            task_by_priority[priority] += 1
        
        logger.debug(f"Generated detailed dashboard for user {user_id} from {start_date} to {end_date}")
        
        return render_template(
            "dashboard_detailed.html",
            start_date=start_date,
            end_date=end_date,
            total_hours=round(total_hours, 2),
            daily_labels=daily_labels,
            daily_hours=daily_hours,
            area_labels=area_labels,
            area_hours=area_hours,
            area_breakdown=area_breakdown,
            task_count=len(ts_logs),
            task_by_priority=task_by_priority,
            time_log_count=len(logs_with_duration),
        )
    except Exception as e:
        logger.error(f"Error generating detailed dashboard: {e}")
        return render_template("dashboard_detailed.html", error=str(e))


@dashboard_bp.route("/api/metrics", methods=["GET"])
@login_required
def api_metrics():
    """API endpoint for detailed metrics data.
    
    Query Parameters:
        from: Start date (ISO format)
        to: End date (ISO format)
    
    Returns:
        JSON with comprehensive metrics and analytics.
    """
    user_id = session["user_id"]
    start_date = request.args.get("from") or (date.today() - timedelta(days=30)).isoformat()
    end_date = request.args.get("to") or date.today().isoformat()
    
    try:
        logs = get_logs_for_range(user_id, start_date, end_date)
        ts_logs = get_ts_logs_for_range(user_id, start_date, end_date)
        
        logs_with_duration = compute_durations(logs)
        ts_durations = compute_ts_durations(ts_logs)
        
        total_hours = sum(log['duration_hours'] for log in logs_with_duration)
        area_breakdown = aggregate_by_area(logs_with_duration)
        
        # Calculate statistics
        if logs_with_duration:
            avg_session = total_hours / len(logs_with_duration) if logs_with_duration else 0
        else:
            avg_session = 0
        
        task_by_status = {}
        for task in ts_logs:
            status = task['status'] or 'Pending'
            if status not in task_by_status:
                task_by_status[status] = 0
            task_by_status[status] += 1
        
        return jsonify({
            'status': 'success',
            'total_hours': round(total_hours, 2),
            'sessions': len(logs_with_duration),
            'avg_session_hours': round(avg_session, 2),
            'tasks': len(ts_logs),
            'area_breakdown': {str(k): v for k, v in area_breakdown.items()},
            'task_status': task_by_status,
        })
    except Exception as e:
        logger.error(f"Error generating metrics API: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
