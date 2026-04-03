"""User settings and preferences module.

This module handles user preferences, customization options, and account settings
such as favorite areas, preferred charge codes, theme selection, and timezone.
"""

import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, flash
from models import (
    get_user_settings,
    update_user_settings,
    get_areas,
    get_charge_codes,
    get_user_custom_areas,
    add_user_custom_area,
    update_user_custom_area,
)
from area_logger import login_required

logger = logging.getLogger(__name__)
settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET"])
@login_required
def index():
    """Display user settings and preferences page.
    
    Returns:
        Rendered settings template with current preferences and available options.
    """
    user_id = session["user_id"]
    
    try:
        # Get current user settings
        settings = get_user_settings(user_id)
        custom_areas = get_user_custom_areas(user_id)
        
        # Get available areas and charge codes
        all_areas = get_areas()
        all_charge_codes = get_charge_codes()
        
        # Parse favorite areas if stored
        favorite_areas = []
        if settings and settings['favorite_areas']:
            try:
                import json
                favorite_areas = json.loads(settings['favorite_areas'])
            except:
                favorite_areas = []
        
        # Parse preferred charge codes if stored
        preferred_codes = []
        if settings and settings['preferred_charge_codes']:
            try:
                import json
                preferred_codes = json.loads(settings['preferred_charge_codes'])
            except:
                preferred_codes = []
        
        logger.debug(f"Loaded settings for user {user_id}")
        
        return render_template(
            "settings.html",
            settings=settings,
            custom_areas=custom_areas,
            all_areas=all_areas,
            all_charge_codes=all_charge_codes,
            favorite_areas=favorite_areas,
            preferred_codes=preferred_codes,
            themes=['light', 'dark', 'auto'],
            timezones=['UTC', 'EST', 'CST', 'MST', 'PST', 'AKST', 'HST'],
        )
    except Exception as e:
        logger.error(f"Error loading settings for user {user_id}: {e}")
        flash("Error loading settings", "error")
        return redirect(url_for("dashboard"))


@settings_bp.route("/update-preferences", methods=["POST"])
@login_required
def update_preferences():
    """Update user preferences.
    
    Form Parameters:
        favorite_areas: JSON string of favorite area IDs
        preferred_charge_codes: JSON string of preferred charge code IDs
        default_area_id: Default area ID
        theme: Theme preference (light/dark/auto)
        timezone: Timezone preference
    
    Returns:
        JSON response with success status or error message.
    """
    user_id = session["user_id"]
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Parse and validate JSON fields
        import json
        
        favorite_areas = data.get('favorite_areas', '[]')
        if isinstance(favorite_areas, str):
            try:
                favorite_areas = json.loads(favorite_areas)
            except:
                favorite_areas = []
        
        preferred_codes = data.get('preferred_charge_codes', '[]')
        if isinstance(preferred_codes, str):
            try:
                preferred_codes = json.loads(preferred_codes)
            except:
                preferred_codes = []
        
        # Update settings in database
        update_user_settings(
            user_id,
            favorite_areas=json.dumps(favorite_areas),
            preferred_charge_codes=json.dumps(preferred_codes),
            default_area_id=data.get('default_area_id'),
            theme=data.get('theme', 'light'),
            timezone=data.get('timezone', 'UTC'),
        )
        
        logger.info(f"Updated preferences for user {user_id}")
        
        if request.is_json:
            return jsonify({'status': 'success', 'message': 'Preferences updated'})
        else:
            flash("Preferences updated successfully", "success")
            return redirect(url_for("settings.index"))
            
    except Exception as e:
        logger.error(f"Error updating preferences for user {user_id}: {e}")
        if request.is_json:
            return jsonify({'status': 'error', 'message': str(e)}), 500
        else:
            flash("Error updating preferences", "error")
            return redirect(url_for("settings.index"))


@settings_bp.route("/customize-area", methods=["POST"])
@login_required
def customize_area():
    """Add or update a customized area for the user.
    
    Form/JSON Parameters:
        area_id: Area ID to customize
        custom_name: Custom name for the area
        is_favorite: Whether to mark as favorite (true/false)
        display_order: Display order preference
    
    Returns:
        JSON response with success status or error message.
    """
    user_id = session["user_id"]
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        area_id = data.get('area_id')
        custom_name = data.get('custom_name')
        is_favorite = data.get('is_favorite', 'false').lower() == 'true'
        display_order = int(data.get('display_order', 0))
        
        if not area_id:
            return jsonify({'status': 'error', 'message': 'Area ID required'}), 400
        
        # Check if custom area already exists
        custom_areas = get_user_custom_areas(user_id)
        existing = next((ca for ca in custom_areas if ca['area_id'] == int(area_id)), None)
        
        if existing:
            # Update existing
            update_user_custom_area(
                existing['id'],
                custom_name=custom_name,
                is_favorite=is_favorite,
                display_order=display_order,
            )
        else:
            # Add new
            add_user_custom_area(
                user_id,
                area_id,
                custom_name=custom_name,
                is_favorite=is_favorite,
                display_order=display_order,
            )
        
        logger.debug(f"Customized area {area_id} for user {user_id}")
        
        return jsonify({'status': 'success', 'message': 'Area customized'})
        
    except Exception as e:
        logger.error(f"Error customizing area for user {user_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@settings_bp.route("/api/preferences", methods=["GET"])
@login_required
def api_preferences():
    """API endpoint to get current user preferences.
    
    Returns:
        JSON with current user settings and customizations.
    """
    user_id = session["user_id"]
    
    try:
        settings = get_user_settings(user_id)
        custom_areas = get_user_custom_areas(user_id)
        
        import json
        
        favorite_areas = []
        preferred_codes = []
        
        if settings:
            if settings['favorite_areas']:
                try:
                    favorite_areas = json.loads(settings['favorite_areas'])
                except:
                    pass
            
            if settings['preferred_charge_codes']:
                try:
                    preferred_codes = json.loads(settings['preferred_charge_codes'])
                except:
                    pass
        
        return jsonify({
            'status': 'success',
            'theme': settings['theme'] if settings else 'light',
            'timezone': settings['timezone'] if settings else 'UTC',
            'favorite_areas': favorite_areas,
            'preferred_charge_codes': preferred_codes,
            'custom_areas': [dict(ca) for ca in custom_areas],
        })
    except Exception as e:
        logger.error(f"Error fetching preferences for user {user_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
