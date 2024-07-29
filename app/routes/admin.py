import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import func
from werkzeug.utils import secure_filename
from datetime import datetime
from app.routes.auth import firebase_db
from .. import sqlalchemy_db as db
from ..models_db import Patient, Doctor
from ..helpers import send_email, send_sms
import google.generativeai as genai

bp = Blueprint('admin', __name__)

GOOGLE_API_KEY1 = ''
genai.configure(api_key=GOOGLE_API_KEY1)

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



#<---------------------- Doctor Management Routes----------------------->

# Doctor Management
@bp.route('/doctors', methods=['GET', 'POST'])
def admin_doctors():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        specialization = request.form.get('specialization')
        license_number = request.form.get('license_number')
        phone_number = request.form.get('phone_number')
        status = request.form.get('status')
        schedule = request.form.get('schedule')
        time = request.form.get('time')

        new_doctor = Doctor(
            first_name=first_name,
            last_name=last_name,
            specialization=specialization,
            license_number=license_number,
            phone_number=phone_number,
            status=status,
            schedule=schedule,
            time=time
        )
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('admin.admin_doctors'))

    doctors = Doctor.query.all()
    return render_template('admin/doctors.html', doctors=doctors)

@bp.route('/doctors/edit/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':
        doctor.first_name = request.form.get('first_name')
        doctor.last_name = request.form.get('last_name')
        doctor.specialization = request.form.get('specialization')
        doctor.license_number = request.form.get('license_number')
        doctor.phone_number = request.form.get('phone_number')
        doctor.status = request.form.get('status')
        doctor.schedule = request.form.get('schedule')
        doctor.time = request.form.get('time')

        db.session.commit()
        flash('Doctor updated successfully!', 'success')
        return redirect(url_for('admin.admin_doctors'))

    return render_template('admin/edit_doctor.html', doctor=doctor)




@bp.route('/admin/doctors/add', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        new_doctor = Doctor(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            specialization=request.form['specialization'],
            license_number=request.form['license_number'],
            phone_number=request.form['phone_number'],
            schedule=request.form['schedule'],
            time=request.form['time']
        )
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('admin.admin_doctors'))
    


@bp.route('/admin/doctors/edit/<int:doctor_id>', methods=['GET', 'POST'])



@bp.route('/admin/doctors/delete/<int:doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor deleted successfully!', 'success')
    return redirect(url_for('admin.admin_doctors'))

# # Department Management
# @bp.route('/admin/departments')
# def admin_departments():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
    
#     departments = Department.query.all()
#     return render_template('admin/departments.html', departments=departments)

# @bp.route('/admin/departments/add', methods=['GET', 'POST'])
# def admin_add_department():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))

#     if request.method == 'POST':
#         name = request.form['name']
#         head = request.form['head']
#         department = Department(name=name, head=head)
#         db.session.add(department)
#         db.session.commit()
#         flash('Department added successfully!', 'success')
#         return redirect(url_for('admin.admin_departments'))

#     return render_template('admin/add_department.html')

# @bp.route('/admin/departments/edit/<int:department_id>', methods=['GET', 'POST'])
# def admin_edit_department(department_id):
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))

#     department = Department.query.get_or_404(department_id)

#     if request.method == 'POST':
#         department.name = request.form['name']
#         department.head = request.form['head']
#         db.session.commit()
#         flash('Department updated successfully!', 'success')
#         return redirect(url_for('admin.admin_departments'))

#     return render_template('admin/edit_department.html', department=department)

# @bp.route('/admin/departments/delete/<int:department_id>', methods=['POST'])
# def admin_delete_department(department_id):
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))

#     department = Department.query.get_or_404(department_id)
#     db.session.delete(department)
#     db.session.commit()
#     flash('Department deleted successfully!', 'success')
#     return redirect(url_for('admin.admin_departments'))

# Resource Management (Budget, Inventory, Facility)


@bp.route('/admin/roles-permissions')
def admin_roles_permissions():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic to display roles and permissions
    return render_template('admin/roles_permissions.html')





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
    # Logic for budget management
    return render_template('admin/budget.html')

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
    # Logic for facilities management
    return render_template('admin/facilities.html')

# Compliance and Security
@bp.route('/admin/security')
def admin_security():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for security settings
    return render_template('admin/security.html')

@bp.route('/admin/privacy')
def admin_privacy():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    # Logic for privacy management
    return render_template('admin/privacy.html')

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