from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import (
    get_charge_codes, get_charge_code_by_id, create_charge_code,
    update_charge_code, delete_charge_code, get_areas_with_charge_codes,
    get_area_by_id, create_area, update_area, delete_area
)
from functools import wraps

management_bp = Blueprint('management', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@management_bp.route('/charge-codes')
@login_required
def charge_codes_list():
    """List all charge codes"""
    charge_codes = get_charge_codes()
    return render_template('charge_codes.html', charge_codes=charge_codes)

@management_bp.route('/charge-codes/create', methods=['GET', 'POST'])
@login_required
def create_charge_code_view():
    """Create a new charge code"""
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()

        if not code:
            flash('Charge code is required', 'error')
            return render_template('charge_code_form.html')

        try:
            create_charge_code(code, description)
            flash('Charge code created successfully', 'success')
            return redirect(url_for('management.charge_codes_list'))
        except Exception as e:
            flash(f'Error creating charge code: {str(e)}', 'error')

    return render_template('charge_code_form.html')

@management_bp.route('/charge-codes/<int:charge_code_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_charge_code_view(charge_code_id):
    """Edit an existing charge code"""
    charge_code = get_charge_code_by_id(charge_code_id)
    if not charge_code:
        flash('Charge code not found', 'error')
        return redirect(url_for('management.charge_codes_list'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()

        if not code:
            flash('Charge code is required', 'error')
            return render_template('charge_code_form.html', charge_code=charge_code)

        try:
            update_charge_code(charge_code_id, code, description)
            flash('Charge code updated successfully', 'success')
            return redirect(url_for('management.charge_codes_list'))
        except Exception as e:
            flash(f'Error updating charge code: {str(e)}', 'error')

    return render_template('charge_code_form.html', charge_code=charge_code)

@management_bp.route('/charge-codes/<int:charge_code_id>/delete', methods=['POST'])
@login_required
def delete_charge_code_view(charge_code_id):
    """Delete a charge code"""
    try:
        delete_charge_code(charge_code_id)
        flash('Charge code deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting charge code: {str(e)}', 'error')

    return redirect(url_for('management.charge_codes_list'))

@management_bp.route('/areas')
@login_required
def areas_list():
    """List all areas with their charge codes"""
    areas = get_areas_with_charge_codes()
    return render_template('areas.html', areas=areas)

@management_bp.route('/areas/create', methods=['GET', 'POST'])
@login_required
def create_area_view():
    """Create a new area"""
    charge_codes = get_charge_codes()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        charge_code_id = request.form.get('charge_code_id')
        description = request.form.get('description', '').strip()

        if not name:
            flash('Area name is required', 'error')
            return render_template('area_form.html', charge_codes=charge_codes)

        try:
            create_area(name, charge_code_id, description)
            flash('Area created successfully', 'success')
            return redirect(url_for('management.areas_list'))
        except Exception as e:
            flash(f'Error creating area: {str(e)}', 'error')

    return render_template('area_form.html', charge_codes=charge_codes)

@management_bp.route('/areas/<int:area_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_area_view(area_id):
    """Edit an existing area"""
    area = get_area_by_id(area_id)
    charge_codes = get_charge_codes()

    if not area:
        flash('Area not found', 'error')
        return redirect(url_for('management.areas_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        charge_code_id = request.form.get('charge_code_id')
        description = request.form.get('description', '').strip()

        if not name:
            flash('Area name is required', 'error')
            return render_template('area_form.html', area=area, charge_codes=charge_codes)

        try:
            update_area(area_id, name, charge_code_id, description)
            flash('Area updated successfully', 'success')
            return redirect(url_for('management.areas_list'))
        except Exception as e:
            flash(f'Error updating area: {str(e)}', 'error')

    return render_template('area_form.html', area=area, charge_codes=charge_codes)

@management_bp.route('/areas/<int:area_id>/delete', methods=['POST'])
@login_required
def delete_area_view(area_id):
    """Delete an area"""
    try:
        delete_area(area_id)
        flash('Area deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting area: {str(e)}', 'error')

    return redirect(url_for('management.areas_list'))