import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import func
from werkzeug.utils import secure_filename
from datetime import datetime

from .. import sqlalchemy_db as db
from ..models_db import Patient, Doctor
from ..helpers import send_email, send_sms

bp = Blueprint('admin', __name__)


# Dashboard Overview
@bp.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    return render_template('admin/dashboard.html')

# # Doctor Management
# @bp.route('/admin/doctors')
# def admin_doctors():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
    
#     doctors = Doctor.query.all()
#     return render_template('admin/doctors.html', doctors=doctors)

# @bp.route('/admin/doctors/add', methods=['GET', 'POST'])
# def admin_add_doctor():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))

#     if request.method == 'POST':
#         name = request.form['name']
#         specialization = request.form['specialization']
#         doctor = Doctor(name=name, specialization=specialization)
#         db.session.add(doctor)
#         db.session.commit()
#         flash('Doctor added successfully!', 'success')
#         return redirect(url_for('admin.admin_doctors'))

#     return render_template('admin/add_doctor.html')

# @bp.route('/admin/doctors/edit/<int:doctor_id>', methods=['GET', 'POST'])
# def admin_edit_doctor(doctor_id):
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))

#     doctor = Doctor.query.get_or_404(doctor_id)

#     if request.method == 'POST':
#         doctor.name = request.form['name']
#         doctor.specialization = request.form['specialization']
#         db.session.commit()
#         flash('Doctor updated successfully!', 'success')
#         return redirect(url_for('admin.admin_doctors'))

#     return render_template('admin/edit_doctor.html', doctor=doctor)

# @bp.route('/admin/doctors/delete/<int:doctor_id>', methods=['POST'])
# def admin_delete_doctor(doctor_id):
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))

#     doctor = Doctor.query.get_or_404(doctor_id)
#     db.session.delete(doctor)
#     db.session.commit()
#     flash('Doctor deleted successfully!', 'success')
#     return redirect(url_for('admin.admin_doctors'))

# # # Department Management
# # @bp.route('/admin/departments')
# # def admin_departments():
# #     if 'user' not in session:
# #         return redirect(url_for('auth.signin'))
    
# #     departments = Department.query.all()
# #     return render_template('admin/departments.html', departments=departments)

# # @bp.route('/admin/departments/add', methods=['GET', 'POST'])
# # def admin_add_department():
# #     if 'user' not in session:
# #         return redirect(url_for('auth.signin'))

# #     if request.method == 'POST':
# #         name = request.form['name']
# #         head = request.form['head']
# #         department = Department(name=name, head=head)
# #         db.session.add(department)
# #         db.session.commit()
# #         flash('Department added successfully!', 'success')
# #         return redirect(url_for('admin.admin_departments'))

# #     return render_template('admin/add_department.html')

# # @bp.route('/admin/departments/edit/<int:department_id>', methods=['GET', 'POST'])
# # def admin_edit_department(department_id):
# #     if 'user' not in session:
# #         return redirect(url_for('auth.signin'))

# #     department = Department.query.get_or_404(department_id)

# #     if request.method == 'POST':
# #         department.name = request.form['name']
# #         department.head = request.form['head']
# #         db.session.commit()
# #         flash('Department updated successfully!', 'success')
# #         return redirect(url_for('admin.admin_departments'))

# #     return render_template('admin/edit_department.html', department=department)

# # @bp.route('/admin/departments/delete/<int:department_id>', methods=['POST'])
# # def admin_delete_department(department_id):
# #     if 'user' not in session:
# #         return redirect(url_for('auth.signin'))

# #     department = Department.query.get_or_404(department_id)
# #     db.session.delete(department)
# #     db.session.commit()
# #     flash('Department deleted successfully!', 'success')
# #     return redirect(url_for('admin.admin_departments'))

# # Resource Management (Budget, Inventory, Facility)
# @bp.route('/admin/resources')
# def admin_resources():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic to display resource data
#     return render_template('admin/resources.html')

# @bp.route('/admin/resources/budget', methods=['GET', 'POST'])
# def admin_budget():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for budget management
#     return render_template('admin/budget.html')

# @bp.route('/admin/resources/inventory')
# def admin_inventory():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for inventory management
#     return render_template('admin/inventory.html')

# @bp.route('/admin/resources/facilities')
# def admin_facilities():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for facilities management
#     return render_template('admin/facilities.html')

# # Compliance and Security
# @bp.route('/admin/security')
# def admin_security():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for security settings
#     return render_template('admin/security.html')

# @bp.route('/admin/privacy')
# def admin_privacy():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for privacy management
#     return render_template('admin/privacy.html')

# @bp.route('/admin/policy')
# def admin_policy():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for policy management
#     return render_template('admin/policy.html')

# # Support
# @bp.route('/admin/support/help-center')
# def admin_help_center():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for help center
#     return render_template('admin/help_center.html')

# @bp.route('/admin/support/contact')
# def admin_contact_support():
#     if 'user' not in session:
#         return redirect(url_for('auth.signin'))
#     # Logic for contacting support
#     return render_template('admin/contact_support.html')

# # Logout
# @bp.route('/logout')
# def logout():
#     session.clear()
#     return redirect(url_for('auth.signin'))