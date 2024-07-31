import os
from flask import Blueprint, flash, jsonify, render_template, request, session, redirect, url_for
from flask_login import current_user, login_required
import pytz
import requests
import pyrebase
from app.config import Config
from app.routes.auth import firebase_db
from ..models_db import Patient, Doctor, Appointment, Message, Prescription, Settings, User, ClientAccounts, Department
from .. import sqlalchemy_db as db
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
import google.generativeai as genai
from PIL import Image
from firebase_admin import auth, exceptions
from flask_paginate import Pagination, get_page_parameter
from app.helpers import send_email, send_sms
from sqlalchemy import func, or_

# Configure your Google Gemini API key
GOOGLE_API_KEY1 = ''
genai.configure(api_key=GOOGLE_API_KEY1)


bp = Blueprint('doctor', __name__)


#<---------------------- doctor Dashboard Routes----------------------->
@bp.route('/doctor')
def doctor_dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    return render_template('doctors/dashboard.html')
# @bp.route('/doctor')
# def doctor_dashboard():
#     if 'user' not in session or session.get('user_type') != 'doctors':
#         return render_template('auth/signin.html') + '''
#             <script>
#                 showFlashMessage('You must be signed in to access this page.', 'red', 'error');
#             </script>
#         '''

#     user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
#     id_token = session.get('user_id_token')  # Also ensure that the Firebase ID token is stored in session

#     try:
#         # Fetch doctor data from Firebase
#         doctor_data = firebase_db.child("Doctors").child(user_id).get(token=id_token).val()
#         if doctor_data:
#             first_name = doctor_data.get('first_name')
#             last_name = doctor_data.get('last_name')
#             total_patients = len(doctor_data.get('patients', []))  # Assuming you store a list of patient IDs
#             total_appointments = len(doctor_data.get('appointments', []))  # Assuming appointments are stored similarly

#             return render_template('doctors/dashboard.html',
#                                       first_name=first_name,
#                                       last_name = last_name
#                                    )
#         else:
#             return render_template('auth/signin.html') + '''
#                 <script>
#                     showFlashMessage('Unable to fetch organization details.', 'red', 'error');
#                 </script>
#             '''
#     except Exception as e:
#         print(f"Firebase fetch error: {e}")
#         return render_template('auth/signin.html') + '''
#             <script>
#                 showFlashMessage('Error accessing organization information.', 'red', 'error');
#             </script>
#         '''


#<----------------------Image Analysis----------------------->
# Allowed extensions for image upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/image-analysis', methods=['GET', 'POST'])
def image_analysis():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    results = None
    if request.method == 'POST':
        if 'image' not in request.files:
            return render_template('doctors/image_analysis.html', results=results) + '''
            <script>
                showFlashMessage('There is no file part, please select a file to analyze.', 'red');
            </script>
            '''
        file = request.files['image']
        if file.filename == '':
            return render_template('doctors/image_analysis.html', results=results) + '''
            <script>
                showFlashMessage('There is no selected file, please select a file to analyze.', 'red');
            </script>
            '''
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join('static', 'uploads', filename)

            # Ensure the uploads directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            file.save(file_path)

            try:
                # Process the image with Gemini API
                img = Image.open(file_path)
                response = genai.GenerativeModel('gemini-pro-vision').generate_content(
                    ["diagnose this medical image in a short sentence", img], stream=False)
                response.resolve()
                results = {
                    'image_url': 'uploads/' + filename,
                    'filename': filename[:10] + '...' if len(filename) > 13 else filename,
                    'filesize': f"{os.path.getsize(file_path) / 1024:.2f} KB",
                    'analysis': response.text
                }
                return render_template('doctors/image_analysis.html', results=results) + '''
                <script>
                    hideLoading();
                    showFlashMessage('Image analyzed successfully!', 'green');
                </script>
                '''
            except Exception as e:
                return render_template('doctors/image_analysis.html', results=results) + f'''
                <script>
                    hideLoading();
                    showFlashMessage('Error processing image: {str(e)}', 'red');
                </script>
                '''
        else:
            return render_template('doctors/image_analysis.html', results=results) + '''
            <script>
                showFlashMessage('File type not allowed', 'red');
            </script>'''
    return render_template('doctors/image_analysis.html', results=results)



#<----------------------Predictive Analytics----------------------->
@bp.route('/predictive_analytics', methods=['GET', 'POST'])
def predictive_analytics():
    patients = Patient.query.all()
    predictions = None
    visualizations = None
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        patient = Patient.query.get(patient_id)
        
        # Process the patient data and make predictions
        predictions = {
            'primary_condition': 'Hypertension',
            'secondary_conditions': ['Type 2 Diabetes', 'Obesity'],
            'risk_level': 'Moderate',
            'cardiovascular_risk': 'High',
            'readmission_risk': 'Low',
            'medication_adherence': 'Poor',
            'lifestyle_recommendations': [
                'Increase physical activity',
                'Reduce sodium intake',
                'Monitor blood glucose daily'
            ],
            'follow_up': {
                'primary_care': '2 weeks',
                'cardiology': '1 month',
                'endocrinology': '3 months'
            },
            'lab_tests': [
                'HbA1c',
                'Lipid panel',
                'Kidney function test'
            ],
            'predicted_outcomes': {
                '3_month': 'Stable',
                '6_month': 'Improved',
                '1_year': 'Significantly improved'
            },
            'care_plan': {
                'medication_adjustments': 'Increase ACE inhibitor dosage',
                'lifestyle_interventions': 'Enroll in diabetes management program',
                'monitoring': 'Weekly blood pressure checks'
            },
            'social_determinants': {
                'transportation_needs': 'Assistance required',
                'food_security': 'At risk',
                'social_support': 'Limited'
            },
            'preventive_care': [
                'Flu vaccination',
                'Pneumococcal vaccination',
                'Colorectal cancer screening'
            ],
            'mental_health': {
                'depression_risk': 'Moderate',
                'anxiety_level': 'Low',
                'stress_management': 'Recommend mindfulness program'
            }
        }
        
        # Create dummy data for visualizations
        visualizations = {
            'age_distribution': [5, 10, 15, 20, 25],
            'weight_height': [
                {'x': 160, 'y': 60},
                {'x': 170, 'y': 70},
                {'x': 180, 'y': 80},
                {'x': 190, 'y': 90},
            ],
            'bmi_distribution': [5, 15, 10, 7],
            'condition_prediction': [10, 5, 3]
        }
        
        return render_template('doctors/predictive_analytics.html', patients=patients, patient=patient, predictions=predictions, visualizations=visualizations)
    
    return render_template('doctors/predictive_analytics.html', patients=patients)



#<----------------------Get Patient Details----------------------->
@bp.route('/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return jsonify({
        'age': patient.age,
        'gender': patient.gender,
        'weight': patient.weight,
        'height': patient.height,
        'medical_history': patient.medical_history,
        # Add other patient details as needed
    })

@bp.route('/dashboard/doctors', methods=['GET'])
def doctors():
    doctor_name = request.args.get('doctor_name', '').strip()
    specialization = request.args.get('specialization', '')
    status = request.args.get('status', '')

    search_query = request.args.get('search', '').strip()
    specialization_filter = request.args.get('specialization', 'All')
    status_filter = request.args.get('status', 'All').lower()  # Convert to lowercase
    
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10  # Number of items per page
    
    doctors_query = Doctor.query
    total = doctors_query.count()
    pagination = doctors_query.paginate(page=page, per_page=per_page, error_out=False)
    doctors = pagination.items
    query = Doctor.query
    if doctor_name:
        query = query.filter(Doctor.first_name.ilike(f'%{doctor_name}%') | Doctor.last_name.ilike(f'%{doctor_name}%'))

    if specialization and specialization != "All":
        query = query.filter(Doctor.specialization == specialization)

    if status and status != "All":
        query = query.filter(Doctor.status == status)
    doctors = query.all()
    specializations = [s.specialization for s in Doctor.query.with_entities(Doctor.specialization).distinct()]
    
    return render_template('doctors/doctors.html', doctors=doctors, search_query=search_query, specialization_filter=specialization_filter, status_filter=status_filter, pagination=pagination, specializations=specializations)






#<----------------------Add Doctor----------------------->
@bp.route('/dashboard/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        doctor = Doctor(name=name, specialization=specialization)
        db.session.add(doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('doctor.doctors'))

    return render_template('add_doctor.html')


#<----------------------View Doctor Profile----------------------->
@bp.route('/dashboard/view_doctor_profile/<int:doctor_id>', methods=['GET'])
def view_doctor_profile(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return render_template('view_doctor_profile.html', doctor=doctor)


#<----------------------Edit Doctor Profile----------------------->
@bp.route('/doctor/edit/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.specialization = request.form['specialization']
        db.session.commit()
        flash('Doctor updated successfully!', 'success')
        return redirect(url_for('doctor.doctors'))

    return render_template('edit_doctor.html', doctor=doctor)


@bp.route('/doctor/delete/<int:doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor deleted successfully!', 'success')
    return redirect(url_for('doctor.doctors'))


#<----------------------patients----------------------->
@bp.route('/patients', methods=['GET', 'POST'])
def patients():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    patients_query = Patient.query.join(Doctor, Patient.doctor_id == Doctor.doctor_id)

    if search_query:
        patients_query = patients_query.filter(
            or_(Patient.first_name.ilike(f'%{search_query}%'),
                Patient.last_name.ilike(f'%{search_query}%'),
                Doctor.first_name.ilike(f'%{search_query}%'),
                Doctor.last_name.ilike(f'%{search_query}%'))
        )

    if status_filter:
        patients_query = patients_query.filter(Patient.status == status_filter)

    pagination = patients_query.paginate(page=page, per_page=7)

    return render_template('doctors/patients.html',
                           patients=pagination.items,
                           pagination=pagination,
                           search_query=search_query,
                           status_filter=status_filter)


@bp.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.name = request.form['name']
        patient.age = request.form['age']
        patient.gender = request.form['gender']
        patient.status = request.form['status']
        db.session.commit()
        return redirect(url_for('doctor.patients'))
    return render_template('edit_patient.html', patient=patient)

@bp.route('/update_patient_status/<int:patient_id>/<string:status>', methods=['POST'])
def update_patient_status(patient_id, status):
    patient = Patient.query.get_or_404(patient_id)
    patient.status = status
    db.session.commit()
    flash('Patient status updated successfully.', 'success')
    return redirect(url_for('doctor.patients'))



#<----------------------Messages----------------------->
@bp.route('/messages', methods=['GET'])
def messages():
    if 'user' not in session or session.get('user_type') != 'organization':
        return redirect(url_for('auth.signin'))

    doctor_id = session.get('user_id')
    messages = Message.query.filter_by(recipient_id=doctor_id).all()
    message_details = []

    for message in messages:
        patient = User.query.filter_by(user_id=message.sender_id).first()
        if patient:
            message_details.append({
                'patient_name': f"{patient.first_name} {patient.last_name}",
                'body': message.body,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })

    return render_template('doctors/messages.html', messages=message_details)

@bp.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    sender_id = session.get('user_id')
    receiver_id = data.get('patient_id')
    body = data.get('message')
    timestamp = datetime.utcnow()

    if not sender_id or not receiver_id or not body:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    new_message = Message(
        sender_id=sender_id,
        recipient_id=receiver_id,
        body=body,
        timestamp=timestamp
    )
    db.session.add(new_message)
    db.session.commit()

    return jsonify({'success': True}), 200



#<----------------------Reports----------------------->
@bp.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    return render_template('doctors/reports.html')


#<----------------------prescription and medical history----------------------->
@bp.route('/prescription', methods=['GET', 'POST'])
def prescription():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    return render_template('doctors/prescription.html')


#<----------------------Appointments----------------------->
@bp.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'user' not in session or session.get('user_type') != 'doctors':
            return redirect(url_for('auth.signin'))

    doctor_id = session.get('user_id')
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    page = request.args.get('page', 1, type=int)

    appointments_query = Appointment.query.filter_by(doctor_id=doctor_id).join(ClientAccounts)

    if search_query:
        search_pattern = f'%{search_query}%'
        appointments_query = appointments_query.filter(
            (ClientAccounts.first_name.ilike(search_pattern)) |
            (ClientAccounts.last_name.ilike(search_pattern))
        )

    if status_filter:
        appointments_query = appointments_query.filter(Appointment.status == status_filter)

    if date_filter:
        try:
            date_filter = datetime.strptime(date_filter, '%Y-%m-%d').date()
            appointments_query = appointments_query.filter(Appointment.appointment_date == date_filter)
        except ValueError:
            flash('Invalid date format', 'error')

    pagination = appointments_query.paginate(page=page, per_page=7)
    appointments = pagination.items

    return render_template('doctors/appointments.html', appointments=appointments, pagination=pagination, search_query=search_query, status_filter=status_filter, date_filter=date_filter)

@bp.route('/dashboard/reschedule_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def reschedule_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    if request.method == 'POST':
        new_date = request.form.get('new_date')
        new_time = request.form.get('new_time')

        if not new_date or not new_time:
            flash('Both date and time are required.', 'error')
            return redirect(url_for('doctor.reschedule_appointment', appointment_id=appointment_id))

        try:
            appointment.date = datetime.strptime(new_date, '%Y-%m-%d')
            appointment.time = datetime.strptime(new_time, '%H:%M').time()
            appointment.status = 'Rescheduled'
            db.session.commit()
            flash('Appointment rescheduled successfully.', 'success')
            return redirect(url_for('doctor.appointments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error rescheduling appointment: {str(e)}', 'error')
            return redirect(url_for('doctor.reschedule_appointment', appointment_id=appointment_id))

    return render_template('reschedule_appointment.html', appointment=appointment)

@bp.route('/dashboard/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if request.method == 'POST':
        appointment.status = request.form['status']
        db.session.commit()
        # flash('Appointment status updated successfully.', 'success')
        return redirect(url_for('doctor.appointments'))
    
    # Fetching patient's last visit or medical history if available
    patient = appointment.patient
    last_visit = patient.last_visit.strftime('%B %d, %Y') if patient.last_visit else 'No previous visit'
    medical_history = patient.medical_history if patient.medical_history else 'No medical history available'
    
    return render_template('edit_appointment.html', appointment=appointment, last_visit=last_visit, medical_history=medical_history)


#<----------------------Lab Results----------------------->
@bp.route('/lab_results', methods=['GET', 'POST'])
def lab_results():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        results = request.form['results']
        patient = Patient.query.get(patient_id)
        patient.lab_results = results
        db.session.commit()
        flash('Lab results updated successfully!', 'success')
        return redirect(url_for('doctor.lab_results'))

    patients = Patient.query.all()
    return render_template('doctors/lab_results.html', patients=patients)

@bp.route('/update_status/<int:appointment_id>/<status>', methods=['POST'])
def update_status(appointment_id, status):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = status
    db.session.commit()

    return redirect(url_for('doctor.appointments'))

@bp.route('/monitor', methods=['GET'])
def monitor():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    patients = Patient.query.all()
    return render_template('doctors/monitor.html', patients=patients)


    
    if notification_type == 'email' and user.settings.email_notifications:
        # Implement email sending logic here
        return jsonify({'success': True, 'message': 'Test email sent successfully'})
    elif notification_type == 'sms' and user.settings.sms_notifications:
        # Implement SMS sending logic here
        return jsonify({'success': True, 'message': 'Test SMS sent successfully'})
    
    return jsonify({'success': False, 'message': 'Notification type not enabled'}), 400


#<----------------------Firebase Authentication----------------------->

def firebase_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = request.cookies.get('token')
        if not id_token:
            return redirect(url_for('auth.signin'))
        try:
            decoded_token = auth.verify_id_token(id_token)
            session['user_id'] = decoded_token['uid']
            session['email'] = decoded_token['email']
        except Exception as e:
            flash('Authentication failed. Please sign in again.', 'error')
            return redirect(url_for('auth.signin'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/settings', methods=['GET', 'POST'])
@firebase_login_required
def settings():
    user = User.query.filter_by(email=session.get('email')).first()

    if not user:
        user = User(email=session.get('email'), user_type='doctor')
        db.session.add(user)
        db.session.commit()

    if not user.settings:
        user.settings = Settings(user_id=user.user_id)
        db.session.add(user.settings)
        db.session.commit()

    if request.method == 'POST':
        try:
            # General Settings
            user.settings.language = request.form.get('language')
            user.settings.timezone = request.form.get('timezone')
            user.settings.dark_mode = 'dark_mode' in request.form
            
            # Patient Management Settings
            user.settings.default_patient_view = request.form.get('default_view')
            user.settings.show_inactive_patients = 'show_inactive' in request.form
            user.settings.records_per_page = int(request.form.get('records_per_page', 20))
            
            # Doctor Management Settings
            user.settings.default_specialization_filter = request.form.get('specialization_filter')
            user.settings.show_doctor_schedules = 'show_schedule' in request.form
            
            # Analytics Settings
            user.settings.default_chart_type = request.form.get('default_chart')
            user.settings.auto_refresh_analytics = 'auto_refresh' in request.form
            user.settings.refresh_interval = int(request.form.get('refresh_interval', 5))
            
            # Notification Settings
            user.settings.email_notifications = 'email_notifications' in request.form
            user.settings.sms_notifications = 'sms_notifications' in request.form
            user.settings.notification_frequency = request.form.get('notification_frequency')
            
            # Security Settings
            user.settings.two_factor_auth = 'two_factor_auth' in request.form
            user.settings.session_timeout = int(request.form.get('session_timeout', 30))
            user.settings.password_expiry = int(request.form.get('password_expiry', 90))
            
            db.session.commit()
            flash('Settings updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating settings: {str(e)}', 'error')
        
        return redirect(url_for('doctors.settings'))
    
    timezones = pytz.all_timezones
    specializations = ['Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'General Surgery', 'Psychiatry', 'Endocrinology']
    
    return render_template('doctors/settings.html', 
                           settings=user.settings, 
                           timezones=timezones, 
                           specializations=specializations)

@bp.route('/settings/toggle_dark_mode', methods=['POST'])
@firebase_login_required
def toggle_dark_mode():
    user = User.query.filter_by(email=session.get('email')).first()
    if user and user.settings:
        user.settings.dark_mode = not user.settings.dark_mode
        db.session.commit()
        return jsonify({'success': True, 'dark_mode': user.settings.dark_mode})
    return jsonify({'success': False}), 400

@bp.route('/settings/update_timezone', methods=['POST'])
@firebase_login_required
def update_timezone():
    user = User.query.filter_by(email=session.get('email')).first()
    if user and user.settings:
        new_timezone = request.json.get('timezone')
        if new_timezone in pytz.all_timezones:
            user.settings.timezone = new_timezone
            db.session.commit()
            return jsonify({'success': True, 'timezone': user.settings.timezone})
    return jsonify({'success': False}), 400

@bp.route('/settings/test_notification', methods=['POST'])
@firebase_login_required
def test_notification():
    notification_type = request.json.get('type')
    user = User.query.filter_by(email=session.get('email')).first()
    
    if notification_type == 'email' and user.settings.email_notifications:
        # Implement email sending logic here
        return jsonify({'success': True, 'message': 'Test email sent successfully'})
    elif notification_type == 'sms' and user.settings.sms_notifications:
        # Implement SMS sending logic here
        return jsonify({'success': True, 'message': 'Test SMS sent successfully'})
    
    return jsonify({'success': False, 'message': 'Notification type not enabled'}), 400