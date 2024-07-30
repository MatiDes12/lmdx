import csv
import io
import os
import re
from flask import Blueprint, jsonify, render_template, request, redirect, send_file, url_for, session, flash
from sqlalchemy import func
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app.routes.auth import firebase_db
from .. import sqlalchemy_db as db
from ..models_db import Appointment, AuditLog, BudgetCategory, Compliance, Department, Facility, Patient, Doctor, Permission, Project, Revenue, Role, RolePermission, Staff, User, UserRole
from ..helpers import send_email, send_sms
import google.generativeai as genai
from werkzeug.security import generate_password_hash
from werkzeug.exceptions import BadRequestKeyError
from flask import request

bp = Blueprint('admin', __name__)

GOOGLE_API_KEY1 = ''
genai.configure(api_key=GOOGLE_API_KEY1)

#<---------------------- index Routes----------------------->
@bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    if session.get('user_type') == 'organization':
        return redirect(url_for('admin.admin_dashboard'))
    elif session.get('user_type') == 'patient':
        return redirect(url_for('patient.patient_dashboard'))
    return redirect(url_for('auth.signin'))


#<---------------------- admin Dashboard Routes----------------------->
@bp.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    return render_template('admin/dashboard.html')

#<---------------------- organization Dashboard Routes----------------------->
@bp.route('/organization')
def organization_dashboard():
    if 'user' not in session or session.get('user_type') != 'organization':
        return render_template('auth/signin.html') + '''
            <script>
                showFlashMessage('You must be signed in to access this page.', 'red', 'error');
            </script>
        '''

    user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    id_token = session.get('user_id_token')  # Also ensure that the Firebase ID token is stored in session

    try:
        # Fetch doctor data from Firebase
        doctor_data = firebase_db.child("Organization").child(user_id).get(token=id_token).val()
        if doctor_data:
            full_name = doctor_data.get('full_name')
            total_patients = len(doctor_data.get('patients', []))  # Assuming you store a list of patient IDs
            total_appointments = len(doctor_data.get('appointments', []))  # Assuming appointments are stored similarly

            return render_template('doctors/dashboard.html',
                                      full_name=full_name,
                                   )
        else:
            return render_template('auth/signin.html') + '''
                <script>
                    showFlashMessage('Unable to fetch organization details.', 'red', 'error');
                </script>
            '''
    except Exception as e:
        print(f"Firebase fetch error: {e}")
        return render_template('auth/signin.html') + '''
            <script>
                showFlashMessage('Error accessing organization information.', 'red', 'error');
            </script>
        '''

#<---------------------- Patient Dashboard Routes----------------------->

@bp.route('/patient')
def patient_dashboard():
    if 'user' not in session or session.get('user_type') != 'patient':
        return render_template('auth/signin.html') + '''
            <script>
                showFlashMessage('You must be signed in to access this page.', 'red', 'error');
            </script>
        '''

    user_id = session.get('user_id')
    id_token = session.get('user_id_token')

    try:
        # Fetch user data from Firebase
        user_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
        if user_data:
            first_name = user_data.get('first_name')
            last_name = user_data.get('last_name')
            return render_template('clients/dashboard.html', first_name=first_name, last_name=last_name)
        else:
            return render_template('auth/signin.html') + '''
                <script>
                    showFlashMessage('Unable to fetch user details.', 'red', 'error');
                </script>
            '''
    except Exception as e:
        print(f"Firebase fetch error: {e}")
        return render_template('auth/signin.html') + '''
            <script>
                showFlashMessage('Error accessing user information.', 'red', 'error');
            </script>
        '''


# <---------------------- Doctor Management Routes ----------------------->
@bp.route('/doctors')
def admin_doctors():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    page = request.args.get('page', 1, type=int)
    per_page = 7
    doctors_pagination = Doctor.query.paginate(page=page, per_page=per_page, error_out=False)
    doctors = doctors_pagination.items
    
    # Generate time slots
    time_slots = [(datetime(2000, 1, 1, hour, 0).strftime('%I:%M %p')) for hour in range(24)]

    # Days of the week
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    return render_template('admin/doctors.html', doctors=doctors, doctors_pagination=doctors_pagination, time_slots=time_slots, days_of_week=days_of_week)


@bp.route('/add_doctor', methods=['POST'])
def add_doctor():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    data = request.form
    try:
        new_doctor = Doctor(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            specialization=data.get('specialization'),
            license_number=data.get('license_number'),
            phone_number=data.get('phone_number'),
            status=data.get('status'),
            schedule=f"{data.get('start_schedule')} to {data.get('end_schedule')}",  # Store schedule as "day to day"
            time=f"{data.get('start_time')} - {data.get('end_time')}"  # Combine start and end times
        )
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding doctor: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_doctors'))

@bp.route('/edit_doctor/<int:doctor_id>', methods=['POST'])
def edit_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    doctor = Doctor.query.get_or_404(doctor_id)
    data = request.form
    try:
        doctor.first_name = data.get('first_name')
        doctor.last_name = data.get('last_name')
        doctor.specialization = data.get('specialization')
        doctor.license_number = data.get('license_number')
        doctor.phone_number = data.get('phone_number')
        doctor.status = data.get('status')
        doctor.schedule = f"{data.get('start_schedule')} to {data.get('end_schedule')}"  # Store schedule as "day to day"
        doctor.time = f"{data.get('start_time')} - {data.get('end_time')}"  # Combine start and end times
        db.session.commit()
        flash('Doctor updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating doctor: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_doctors'))



@bp.route('/delete_doctor/<int:doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    doctor = Doctor.query.get_or_404(doctor_id)
    try:
        db.session.delete(doctor)
        db.session.commit()
        flash('Doctor deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting doctor: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_doctors'))
# <---------------------- Doctor Management Endpoints ----------------------->


@bp.route('/get_doctor/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    doctor = Doctor.query.get_or_404(doctor_id)
    return jsonify({
        'doctor_id': doctor.doctor_id,
        'first_name': doctor.first_name,
        'last_name': doctor.last_name,
        'specialization': doctor.specialization,
        'license_number': doctor.license_number,
        'phone_number': doctor.phone_number,
        'status': doctor.status,
        'schedule': doctor.schedule,
        'time': doctor.time
    })



# <-------------------- Departments Management Routes -------------------->
@bp.route('/admin/departments')
def admin_departments():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    departments = Department.query.all()
    total_departments = Department.query.count()
    staff_members = Staff.query.all()
    return render_template('admin/departments.html', departments=departments, total_departments=total_departments, staff_members=staff_members)

@bp.route('/admin/departments/add', methods=['POST'])
def admin_add_department():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    name = request.form['name']
    head = request.form['head']
    department = Department(name=name, head=head)
    db.session.add(department)
    db.session.commit()
    flash('Department added successfully!', 'success')
    return redirect(url_for('admin.admin_departments'))

@bp.route('/admin/departments/edit/<int:department_id>', methods=['GET', 'POST'])
def admin_edit_department(department_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    department = Department.query.get_or_404(department_id)

    if request.method == 'POST':
        department.name = request.form['name']
        department.head = request.form['head']
        db.session.commit()
        flash('Department updated successfully!', 'success')
        return redirect(url_for('admin.admin_departments'))

    if request.method == 'GET':
        return jsonify({'name': department.name, 'head': department.head})

    return render_template('admin/edit_department.html', department=department)

@bp.route('/admin/departments/delete/<int:department_id>', methods=['POST'])
def admin_delete_department(department_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    department = Department.query.get_or_404(department_id)
    db.session.delete(department)
    db.session.commit()
    flash('Department deleted successfully!', 'success')
    return redirect(url_for('admin.admin_departments'))

@bp.route('/admin/departments/assign-staff', methods=['POST'])
def admin_assign_staff():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    department_id = request.form['department']
    staff_id = request.form['staff']
    # Implement staff assignment logic here
    flash('Staff assigned to department successfully!', 'success')
    return redirect(url_for('admin.admin_departments'))




# <---------------------- Doctor Management Routes ----------------------->
@bp.route('/compliance-tracking')
def compliance_tracking():
    compliances = Compliance.query.join(Doctor).all()
    total_doctors = Doctor.query.count()
    compliant_doctors = Compliance.query.filter_by(status='Compliant').count()
    non_compliant_doctors = total_doctors - compliant_doctors
    compliance_rate = (compliant_doctors / total_doctors) * 100 if total_doctors > 0 else 0

    return render_template('admin/compliance_tracking.html',
                           compliances=compliances,
                           total_doctors=total_doctors,
                           compliant_doctors=compliant_doctors,
                           non_compliant_doctors=non_compliant_doctors,
                           compliance_rate=round(compliance_rate, 2))

@bp.route('/compliance-tracking/update/<int:compliance_id>', methods=['POST'])
def update_compliance(compliance_id):
    compliance = Compliance.query.get_or_404(compliance_id)
    compliance.status = request.form['status']
    db.session.commit()
    flash('Compliance status updated successfully!', 'success')
    return redirect(url_for('admin.compliance_tracking'))

def parse_schedule(schedule_str):
    days_pattern = r"(\w+) to (\w+)"
    time_pattern = r"(\d{2}:\d{2} [AP]M) - (\d{2}:\d{2} [AP]M)"
    
    days_match = re.search(days_pattern, schedule_str)
    time_match = re.search(time_pattern, schedule_str)
    
    schedule = {
        'start_day': days_match.group(1) if days_match else None,
        'end_day': days_match.group(2) if days_match else None,
        'start_time': time_match.group(1) if time_match else None,
        'end_time': time_match.group(2) if time_match else None
    }
    
    return schedule


def parse_schedule_and_time(doctor):
    schedule_parts = doctor.schedule.split(" to ")
    time_parts = doctor.time.split(" - ")
    return {
        'schedule_start': schedule_parts[0],
        'schedule_end': schedule_parts[1],
        'time_start': time_parts[0],
        'time_end': time_parts[1]
    }

# @bp.route('/doctors')
# def display_doctors():
#     doctors = Doctor.query.all()
#     parsed_doctors = [{**doctor.__dict__, **parse_schedule_and_time(doctor)} for doctor in doctors]
#     return render_template('doctors.html', doctors=parsed_doctors)


@bp.route('/admin/roles-permissions')
def admin_roles_permissions():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    roles = Role.query.all()
    permissions = Permission.query.all()
    
    # Count users for each role
    for role in roles:
        role.users_count = UserRole.query.filter_by(role_id=role.role_id).count()
    
    # Get associated roles for each permission
    for permission in permissions:
        associated_roles = RolePermission.query.filter_by(permission_id=permission.permission_id).all()
        permission.associated_roles = [Role.query.get(rp.role_id).role_name for rp in associated_roles]

    total_roles = len(roles)

    return render_template('admin/roles_permissions.html', 
                           roles=roles, 
                           permissions=permissions, 
                           total_roles=total_roles)

@bp.route('/admin/departments/generate-report', methods=['POST'])
def admin_generate_report():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    report_type = request.form['report_type']
    
    if report_type == 'staff_assignment':
        # Generate Staff Assignment Report
        departments = Department.query.all()
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Department', 'Staff Member', 'Position'])
        for department in departments:
            staff_members = Staff.query.filter_by(department=department.name).all()
            for staff in staff_members:
                writer.writerow([department.name, f"{staff.first_name} {staff.last_name}", staff.position])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            attachment_filename=f'staff_assignment_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    
    elif report_type == 'department_summary':
        # Generate Department Summary Report
        departments = Department.query.all()
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Department', 'Head', 'Staff Count', 'Active Projects', 'Completed Projects'])
        for department in departments:
            staff_count = Staff.query.filter_by(department=department.name).count()
            active_projects = Project.query.filter_by(department_id=department.department_id, status='Active').count()
            completed_projects = Project.query.filter_by(department_id=department.department_id, status='Completed').count()
            writer.writerow([department.name, department.head, staff_count, active_projects, completed_projects])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            attachment_filename=f'department_summary_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    
    else:
        flash('Invalid report type selected.', 'error')
        return redirect(url_for('admin.admin_departments'))






@bp.route('/admin/resources')
def admin_resources():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic to display resource data
    return render_template('admin/resources.html')

@bp.route('/admin/resources/budget', methods=['GET', 'POST'])
def admin_budget():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    if request.method == 'POST':
        # Handling form submission
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name')
            allocated = float(request.form.get('allocated', 0))
            spent = float(request.form.get('spent', 0))

            new_category = BudgetCategory(name=name, allocated=allocated, spent=spent)
            db.session.add(new_category)
            db.session.commit()
            flash('New budget category added successfully', 'success')
        elif action == 'update':
            category_id = int(request.form.get('category_id'))
            category = BudgetCategory.query.get(category_id)
            if category:
                category.allocated = float(request.form.get('allocated', category.allocated))
                category.spent = float(request.form.get('spent', category.spent))
                db.session.commit()
                flash('Budget category updated successfully', 'success')
        elif action == 'delete':
            category_id = int(request.form.get('category_id'))
            category = BudgetCategory.query.get(category_id)
            if category:
                db.session.delete(category)
                db.session.commit()
                flash('Budget category deleted successfully', 'success')

    # Fetch budget data from the database
    budget_categories = BudgetCategory.query.all()
    total_budget = sum(category.allocated for category in budget_categories)
    total_income = calculate_total_income()  # Implement this function
    total_expenses = sum(category.spent for category in budget_categories)
    net_balance = total_income - total_expenses

    return render_template('admin/budget.html', 
                           budget_categories=budget_categories,
                           total_budget=total_budget,
                           total_income=total_income,
                           total_expenses=total_expenses,
                           net_balance=net_balance)

def calculate_total_income():
    total_income = db.session.query(db.func.sum(Revenue.amount)).scalar() or 0.0
    return total_income

@bp.route('/admin/resources/inventory')
def admin_inventory():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for inventory management
    return render_template('admin/inventory.html')



@bp.route('/admin/resources/facilities')
def admin_facilities():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    facilities = Facility.query.all()
    total_facilities = len(facilities)
    return render_template('admin/facilities.html', facilities=facilities, total_facilities=total_facilities)

@bp.route('/admin/facilities/add', methods=['POST'])
def add_facility():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    name = request.form['facilityName']
    location = request.form['facilityLocation']
    status = request.form['facilityStatus']

    new_facility = Facility(name=name, location=location, status=status)
    db.session.add(new_facility)
    db.session.commit()

    flash('Facility added successfully!', 'success')
    return redirect(url_for('admin.admin_facilities'))

@bp.route('/admin/facilities/edit/<int:facility_id>', methods=['GET', 'POST'])
def edit_facility(facility_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    facility = Facility.query.get_or_404(facility_id)

    if request.method == 'POST':
        facility.name = request.form['facilityName']
        facility.location = request.form['facilityLocation']
        facility.status = request.form['facilityStatus']
        db.session.commit()
        flash('Facility updated successfully!', 'success')
        return redirect(url_for('admin.admin_facilities'))

    return jsonify({
        'name': facility.name,
        'location': facility.location,
        'status': facility.status
    })

@bp.route('/admin/facilities/delete/<int:facility_id>', methods=['POST'])
def delete_facility(facility_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    facility = Facility.query.get_or_404(facility_id)
    db.session.delete(facility)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Facility deleted successfully'})

@bp.route('/admin/facilities/maintenance/add', methods=['POST'])
def add_maintenance():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    # Add logic to create a new maintenance schedule
    # Similar to add_facility but with maintenance-specific fields

    flash('Maintenance schedule added successfully!', 'success')
    return redirect(url_for('admin.admin_facilities'))

@bp.route('/admin/facilities/maintenance/edit/<int:schedule_id>', methods=['GET', 'POST'])
def edit_maintenance(schedule_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    # Add logic to edit a maintenance schedule
    # Similar to edit_facility but with maintenance-specific fields

    flash('Maintenance schedule updated successfully!', 'success')
    return redirect(url_for('admin.admin_facilities'))

@bp.route('/admin/facilities/maintenance/delete/<int:schedule_id>', methods=['POST'])
def delete_maintenance(schedule_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    # Add logic to delete a maintenance schedule

    return jsonify({'success': True, 'message': 'Maintenance schedule deleted successfully'})


@bp.route('/admin/projects')
def admin_projects():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for project management
    return render_template('admin/projects.html')

@bp.route('/admin/projects/add', methods=['POST'])
def admin_add_project():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    name = request.form['name']
    description = request.form['description']
    department_id = request.form['department_id']
    status = request.form['status']

    new_project = Project(name=name, description=description, department_id=department_id, status=status)
    db.session.add(new_project)
    db.session.commit()
    flash('Project added successfully!', 'success')
    return redirect(url_for('admin.admin_projects'))

@bp.route('/admin/projects/edit/<int:project_id>', methods=['GET', 'POST'])
def admin_edit_project(project_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form['description']
        project.department_id = request.form['department_id']
        project.status = request.form['status']
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('admin.admin_projects'))

    if request.method == 'GET':
        return jsonify({'name': project.name, 'description': project.description, 'department_id': project.department_id, 'status': project.status})

    return render_template('admin/edit_project.html', project=project)


@bp.route('/admin/audit_logs')
def admin_audit_logs():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    total_logs = AuditLog.query.count()
    today_activities = AuditLog.query.filter(AuditLog.timestamp >= datetime.utcnow().date()).count()

    return render_template('admin/audit_logs.html', 
                           audit_logs=audit_logs,
                           total_logs=total_logs,
                           today_activities=today_activities)

@bp.route('/api/audit-log/<int:log_id>')
def get_audit_log_details(log_id):
    log = AuditLog.query.get_or_404(log_id)
    return jsonify({
        'user': log.user.username,
        'action': log.action,
        'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'details': log.details
    })

@bp.route('/admin/audit_logs/export', methods=['POST'])
def export_audit_logs():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    # Export audit logs to CSV file
    audit_logs = AuditLog.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['User', 'Action', 'Timestamp', 'Details'])
    for log in audit_logs:
        writer.writerow([log.user.username, log.action, log.timestamp, log.details])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename=f'audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@bp.route('/admin/reports')
def admin_reports():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    # Fetch reports from the database
    reports = Report.query.order_by(Report.generated_at.desc()).limit(10).all()
    total_reports = Report.query.count()
    today_reports = Report.query.filter(Report.generated_at >= datetime.utcnow().date()).count()

    return render_template('admin/reports.html', 
                           reports=reports,
                           total_reports=total_reports,
                           today_reports=today_reports)

@bp.route('/api/report/<int:report_id>')
def get_report_details(report_id):
    report = Report.query.get_or_404(report_id)
    return jsonify({
        'report_id': report.report_id,
        'type': report.type,
        'user': {
            'username': report.user.username
        },
        'generated_at': report.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
        'details': report.details
    })

@bp.route('/admin/reports/generate', methods=['POST'])
def generate_report():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    report_type = request.form['reportType']
    date_range = request.form['dateRange']
    user_filter = request.form['userFilter']

    # Logic to generate the report based on the parameters
    # This is a placeholder and should be replaced with actual report generation logic
    new_report = Report(
        type=report_type,
        user_id=session['user']['id'],
        details="Report details would go here"
    )
    db.session.add(new_report)
    db.session.commit()

    flash('Report generated successfully!', 'success')
    return redirect(url_for('admin.admin_reports'))

@bp.route('/admin/reports/delete/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Report deleted successfully'})

@bp.route('/admin/revenue')
def admin_revenue():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    revenues = Revenue.query.all()
    total_revenue = db.session.query(func.sum(Revenue.amount)).scalar() or 0.0
    return render_template('admin/revenue.html', revenues=revenues, total_revenue=total_revenue)

@bp.route('/admin/revenue/add', methods=['POST'])
def add_revenue():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    amount = float(request.form['amount'])
    source = request.form['source']
    description = request.form['description']

    new_revenue = Revenue(amount=amount, source=source, description=description)
    db.session.add(new_revenue)
    db.session.commit()

    flash('Revenue added successfully!', 'success')
    return redirect(url_for('admin.admin_revenue'))

@bp.route('/admin/revenue/edit/<int:revenue_id>', methods=['GET', 'POST'])
def edit_revenue(revenue_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    revenue = Revenue.query.get_or_404(revenue_id)

    if request.method == 'POST':
        revenue.amount = float(request.form['amount'])
        revenue.source = request.form['source']
        revenue.description = request.form['description']
        db.session.commit()
        flash('Revenue updated successfully!', 'success')
        return redirect(url_for('admin.admin_revenue'))

    return jsonify({
        'amount': revenue.amount,
        'source': revenue.source,
        'description': revenue.description
    })

@bp.route('/admin/revenue/delete/<int:revenue_id>', methods=['POST'])
def delete_revenue(revenue_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    revenue = Revenue.query.get_or_404(revenue_id)
    db.session.delete(revenue)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Revenue deleted successfully'})

@bp.route('/admin/revenue/export', methods=['POST'])
def export_revenue():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    revenues = Revenue.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Amount', 'Source', 'Description'])
    for revenue in revenues:
        writer.writerow([revenue.amount, revenue.source, revenue.description])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename=f'revenue_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@bp.route('/admin/admin_performance_analytics')
def admin_performance_analytics():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for performance analytics
    return render_template('admin/performance_analytics.html')


@bp.route('/admin/privacy')
def admin_privacy():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for privacy management
    return render_template('admin/privacy.html')

@bp.route('/admin/security')
def admin_security():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items

    total_users = User.query.count()
    active_sessions = sum(1 for user in User.query.all() if user.active)
    
    return render_template('admin/security.html', users=users, total_users=total_users, active_sessions=active_sessions, pagination=pagination)




@bp.route('/admin/security/add_user', methods=['POST'])
def add_user():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    # Fetching form data
    username = request.form.get('username')
    email = request.form.get('email')
    user_type = request.form.get('role')  # Corrected to match the model's attribute name
    password = request.form.get('password')

    if not (username and email and user_type and password):
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.admin_security'))

    password_hash = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=password_hash, user_type=user_type)

    db.session.add(new_user)
    db.session.commit()
    flash('User added successfully.', 'success')
    return redirect(url_for('admin.admin_security'))


@bp.route('/admin/security/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.user_type = request.form.get('user_type')
        password = request.form.get('password')
        if password:
            user.set_password(password)  # Use method to hash password
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.admin_security'))
    return render_template('admin/edit_user.html', user=user)

@bp.route('/admin/security/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.admin_security'))



@bp.route('/admin/policy')
def admin_policy():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for policy management
    return render_template('admin/policy.html')

# Support
@bp.route('/admin/support/help-center')
def admin_help_center():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for help center
    return render_template('admin/help_center.html')

@bp.route('/admin/support/contact')
def admin_contact_support():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for contacting support
    return render_template('admin/contact_support.html')

# Logout
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.signin'))