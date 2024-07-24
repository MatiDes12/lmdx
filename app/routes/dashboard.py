import os
from flask import Blueprint, flash, jsonify, render_template, request, session, redirect, url_for
import requests
import pyrebase
from app.config import Config
from app.routes.auth import firebase_db
from ..models_db import Patient, Doctor, Appointment, Message
from .. import sqlalchemy_db as db
from datetime import datetime
from werkzeug.utils import secure_filename
import google.generativeai as genai
from PIL import Image
from flask_paginate import Pagination, get_page_parameter
# from ..models.user import User
from app.helpers import send_email, send_sms
from sqlalchemy import func

# Configure your Google Gemini API key
GOOGLE_API_KEY1 = ''
genai.configure(api_key=GOOGLE_API_KEY1)

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    if session.get('user_type') == 'organization':
        return redirect(url_for('dashboard.organization_dashboard'))
    elif session.get('user_type') == 'patient':
        return redirect(url_for('patient.patient_dashboard'))
    return redirect(url_for('auth.signin'))

@bp.route('/organization')
def organization_dashboard():
    if 'user' not in session or session.get('user_type') != 'organization':
        return redirect(url_for('auth.signin'))

    user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    id_token = session.get('user_id_token')  # Also ensure that the Firebase ID token is stored in session

    try:
        # Fetch doctor data from Firebase
        doctor_data = firebase_db.child("DoctorAccounts").child(user_id).get(token=id_token).val()
        if doctor_data:
            doctor_name = doctor_data.get('name')
            total_patients = len(doctor_data.get('patients', []))  # Assuming you store a list of patient IDs
            total_appointments = len(doctor_data.get('appointments', []))  # Assuming appointments are stored similarly

            return render_template('doctors/dashboard.html',
                                   doctor_name=doctor_name,
                                   total_patients=total_patients,
                                   total_appointments=total_appointments)
        else:
            flash('Unable to fetch doctor details.', 'error')
            return redirect(url_for('auth.signin'))
    except Exception as e:
        flash('Error accessing doctor information.', 'error')
        print(f"Firebase fetch error: {e}")
        return redirect(url_for('auth.signin'))

@bp.route('/patient')
def patient_dashboard():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    # user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    # id_token = session.get('user_id_token')  # Also ensure that the Firebase ID token is stored in session
    
    # try:
    #     # Fetch user data from Firebase
    #     user_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
    #     if user_data:
    #         first_name = user_data.get('first_name')
    #         last_name = user_data.get('last_name')
    #         return render_template('clients/dashboard.html', first_name=first_name, last_name=last_name)
    #     else:
    #         flash('Unable to fetch user details.', 'error')
    #         return redirect(url_for('auth.signin'))
    # except Exception as e:
    #     flash('Error accessing user information.', 'error')
    #     print(f"Firebase fetch error: {e}")
    #     return redirect(url_for('auth.signin'))
    return render_template('clients/dashboard.html')



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
            file_path = os.path.join('app', 'static', 'uploads', filename)

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
                return render_template('doctors/nalysis.html', results=results) + '''
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
    search_query = request.args.get('search', '').strip()
    specialization_filter = request.args.get('specialization', 'All')
    status_filter = request.args.get('status', 'All').lower()  # Convert to lowercase
    
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10  # Number of items per page
    
    doctors_query = Doctor.query
    
    if search_query:
        doctors_query = doctors_query.filter(Doctor.name.ilike(f'{search_query}%'))
    
    if specialization_filter != 'All':
        doctors_query = doctors_query.filter_by(specialization=specialization_filter)
    
    if status_filter != 'all':  # Convert to lowercase
        doctors_query = doctors_query.filter(func.lower(Doctor.status) == status_filter)
    
    total = doctors_query.count()
    pagination = doctors_query.paginate(page=page, per_page=per_page, error_out=False)
    doctors = pagination.items
    
    specializations = Doctor.query.with_entities(Doctor.specialization).distinct().all()
    
    return render_template('doctors/doctors.html', doctors=doctors, search_query=search_query, specialization_filter=specialization_filter, status_filter=status_filter, pagination=pagination, specializations=specializations)


    ery.get_or_404(doctor_id)
    if request.method == 'POST':
        # Add your message handling logic here
        pass
    return render_template('message_doctor.html', doctor=doctor)

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
        return redirect(url_for('dashboard.doctors'))

    return render_template('add_doctor.html')

@bp.route('/dashboard/view_doctor_profile/<int:doctor_id>', methods=['GET'])
def view_doctor_profile(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return render_template('view_doctor_profile.html', doctor=doctor)


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
        return redirect(url_for('dashboard.doctors'))

    return render_template('edit_doctor.html', doctor=doctor)

@bp.route('/doctor/delete/<int:doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor deleted successfully!', 'success')
    return redirect(url_for('dashboard.doctors'))

@bp.route('/patients', methods=['GET', 'POST'])
def patients():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    patients_query = Patient.query.join(Doctor)

    if search_query:
        patients_query = patients_query.filter(
            (Patient.name.ilike(f'%{search_query}%')) |
            (Doctor.name.ilike(f'%{search_query}%'))
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
        return redirect(url_for('dashboard.patients'))
    return render_template('edit_patient.html', patient=patient)

@bp.route('/update_patient_status/<int:patient_id>/<string:status>', methods=['POST'])
def update_patient_status(patient_id, status):
    patient = Patient.query.get_or_404(patient_id)
    patient.status = status
    db.session.commit()
    flash('Patient status updated successfully.', 'success')
    return redirect(url_for('dashboard.patients'))

@bp.route('/send_message_page/<int:patient_id>', methods=['GET'])
def send_message_page(patient_id):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    patient = Patient.query.get_or_404(patient_id)
    return render_template('send_message.html', patient=patient)

@bp.route('/send_message', methods=['POST'])
def send_message():
    patient_id = request.form.get('patient_id')
    message_type = request.form.get('message_type')
    content = request.form.get('content')

    patient = Patient.query.get(patient_id)
    if not patient:
        flash('Patient not found', 'danger')
        return redirect(url_for('dashboard.patients'))

    if message_type == 'email':
        success = send_email(patient.email, "Message from Hospital", content)
    elif message_type == 'sms':
        success = send_sms(patient.phone_number, content)
    else:
        flash('Invalid message type', 'danger')
        return redirect(url_for('dashboard.send_message_page', patient_id=patient_id))

    if success:
        message = Message(patient_id=patient.id, message_type=message_type, content=content, status='sent')
        flash('Message sent successfully', 'success')
    else:
        message = Message(patient_id=patient.id, message_type=message_type, content=content, status='failed')
        flash('Failed to send message', 'danger')

    db.session.add(message)
    db.session.commit()
    return redirect(url_for('dashboard.patients'))



@bp.route('/reports')
def reports():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    return render_template('doctors/reports.html')

@bp.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'user' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('auth.signin'))

    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    doctor_id = session.get('user_id')
    appointments_query = Appointment.query.filter_by(doctor_id=doctor_id).join(Patient).join(Doctor)

    if search_query:
        search_pattern = f'%{search_query}%'
        appointments_query = appointments_query.filter(
            (Patient.name.ilike(search_pattern)) |
            (Doctor.name.ilike(search_pattern))
        )

    if status_filter:
        appointments_query = appointments_query.filter(Appointment.status == status_filter)

    pagination = appointments_query.paginate(page=page, per_page=7)
    appointments = pagination.items

    return render_template('doctors/appointments.html', appointments=appointments, pagination=pagination, search_query=search_query, status_filter=status_filter)


@bp.route('/dashboard/reschedule_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def reschedule_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    if request.method == 'POST':
        new_date = request.form.get('new_date')
        new_time = request.form.get('new_time')

        if not new_date or not new_time:
            flash('Both date and time are required.', 'error')
            return redirect(url_for('dashboard.reschedule_appointment', appointment_id=appointment_id))

        try:
            appointment.date = datetime.strptime(new_date, '%Y-%m-%d')
            appointment.time = datetime.strptime(new_time, '%H:%M').time()
            appointment.status = 'Rescheduled'
            db.session.commit()
            flash('Appointment rescheduled successfully.', 'success')
            return redirect(url_for('dashboard.appointments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error rescheduling appointment: {str(e)}', 'error')
            return redirect(url_for('dashboard.reschedule_appointment', appointment_id=appointment_id))

    return render_template('reschedule_appointment.html', appointment=appointment)

@bp.route('/dashboard/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if request.method == 'POST':
        appointment.status = request.form['status']
        db.session.commit()
        # flash('Appointment status updated successfully.', 'success')
        return redirect(url_for('dashboard.appointments'))
    
    # Fetching patient's last visit or medical history if available
    patient = appointment.patient
    last_visit = patient.last_visit.strftime('%B %d, %Y') if patient.last_visit else 'No previous visit'
    medical_history = patient.medical_history if patient.medical_history else 'No medical history available'
    
    return render_template('edit_appointment.html', appointment=appointment, last_visit=last_visit, medical_history=medical_history)


@bp.route('/update_status/<int:appointment_id>/<status>', methods=['POST'])
def update_status(appointment_id, status):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = status
    db.session.commit()

    return redirect(url_for('dashboard.appointments'))

@bp.route('/monitor', methods=['GET'])
def monitor():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    patients = Patient.query.all()
    return render_template('doctors/monitor.html', patients=patients)

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    user = User.query.filter_by(email=session['user']).first()

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        if 'password' in request.form and request.form['password']:
            user.password = request.form['password']  # Make sure to hash the password in a real app

        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('dashboard.settings'))

    return render_template('doctors/settings.html', user=user)

@bp.route('/update_preferences', methods=['POST'])
def update_preferences():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    user = User.query.filter_by(email=session['user']).first()
    user.theme = request.form['theme']
    user.language = request.form['language']

    db.session.commit()
    flash('Preferences updated successfully!', 'success')
    return redirect(url_for('dashboard.settings'))

@bp.route('/update_notifications', methods=['POST'])
def update_notifications():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    user = User.query.filter_by(email=session['user']).first()
    user.email_notifications = request.form['email_notifications']
    user.sms_notifications = request.form['sms_notifications']

    db.session.commit()
    flash('Notification preferences updated successfully!', 'success')
    return redirect(url_for('dashboard.settings'))

@bp.route('/update_security', methods=['POST'])
def update_security():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    user = User.query.filter_by(email=session['user']).first()
    user.two_factor = 'two_factor' in request.form
    user.backup_email = request.form['backup_email']

    db.session.commit()
    flash('Security settings updated successfully!', 'success')
    return redirect(url_for('dashboard.settings'))

@bp.route('/patient/<int:patient_id>', methods=['GET', 'POST'])
def patient_profile(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctors = Doctor.query.all()

    if request.method == 'POST':
        try:
            patient.name = request.form['name']
            patient.age = request.form['age']
            patient.gender = request.form['gender']
            patient.status = request.form['status']
            patient.email = request.form['email']
            patient.phone_number = request.form['phone_number']
            patient.admission_date = datetime.strptime(request.form['admission_date'], '%Y-%m-%d')
            patient.last_visit = datetime.strptime(request.form['last_visit'], '%Y-%m-%d')
            patient.doctor_id = Doctor.query.filter_by(name=request.form['doctor_id']).first().id
            db.session.commit()
            flash('Patient details updated successfully!', 'success')
            return redirect(url_for('dashboard.patient_profile', patient_id=patient.id))
        except Exception as e:
            flash(f'Error updating patient details: {str(e)}', 'error')
            return redirect(url_for('dashboard.patient_profile', patient_id=patient.id))

    return render_template('patient_profile.html', patient=patient, doctors=doctors)


@bp.route('/patient/<int:patient_id>')
def patient_details(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template('patient_details.html', patient=patient)
