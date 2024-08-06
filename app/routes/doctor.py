import os
import random
from flask import Blueprint, flash, jsonify, render_template, request, send_from_directory, session, redirect, url_for
import pytz
from ..models_db import LabResult, LabTest, Patient, Doctor, Appointment, Message, Prescription, Settings, User, Account, ClientAccounts, Notification
from .. import sqlalchemy_db as db
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
import google.generativeai as genai
from PIL import Image
from firebase_admin import auth, exceptions
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import and_, and_, or_
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename


# Define a folder where uploaded images will be stored
UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads', 'lab_results')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure your Google Gemini API key
GOOGLE_API_KEY1 = ''
genai.configure(api_key=GOOGLE_API_KEY1)


bp = Blueprint('doctor', __name__)


#<---------------------- doctor Dashboard Routes----------------------->

@bp.route('/doctor')
def doctor_dashboard():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))
    
    # Retrieve the doctor details using the account ID from the session
    firebase_user_id = session.get('user_id')  # Assuming session stores Firebase ID
    account = Account.query.filter_by(id=firebase_user_id).first()

    if not account:
        return redirect(url_for('auth.signin'))

    doctor_id = account.doctor_id

    # Fetch doctor's first and last name
    doctor = Doctor.query.get(doctor_id)
    first_name = doctor.first_name if doctor else 'Doctor'
    last_name = doctor.last_name if doctor else ''

    # Query for upcoming appointments
    today = datetime.now().date()
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date >= today
    ).order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc()).all()

    # Count unread messages
    unread_messages_count = Message.query.filter_by(recipient_id=firebase_user_id, is_read=False).count()

    # Query for recent unread notifications
    unread_notifications = Notification.query.filter_by(
        doctor_id=doctor_id,
        is_read=False
    ).order_by(Notification.timestamp.desc()).all()

    return render_template(
        'doctors/dashboard.html',
        first_name=first_name,
        last_name=last_name,
        upcoming_appointments=upcoming_appointments,
        unread_messages_count=unread_messages_count,
        notifications=unread_notifications
    )



#<---------------------- AI Suggestions ----------------------->
@bp.route('/ai-suggestions')
def ai_suggestions():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))
    
    return render_template('doctors/dashboard.html')



#<----------------------Appointments----------------------->

@bp.route('/appointments', methods=['GET'])
def appointments():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    firebase_user_id = session.get('user_id')  # Get the Firebase user ID from the session
    account = Account.query.filter_by(id=firebase_user_id).first()

    if not account:
        return redirect(url_for('auth.signin'))

    doctor_id = account.doctor_id

    # Retrieve filter parameters from the query string
    date_filter = request.args.get('date')
    status_filter = request.args.get('status')
    search_query = request.args.get('search')

    # Base query for appointments
    query = Appointment.query.filter_by(doctor_id=doctor_id)

    # Apply filters
    if date_filter:
        query = query.filter(Appointment.appointment_date == date_filter)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    if search_query:
        query = query.join(ClientAccounts).filter(
            or_(
                ClientAccounts.first_name.ilike(f"%{search_query}%"),
                ClientAccounts.last_name.ilike(f"%{search_query}%")
            )
        )

    appointments = query.all()

    return render_template('doctors/appointments.html', appointments=appointments, date_filter=date_filter, status_filter=status_filter, search_query=search_query)


@bp.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    appointment = Appointment.query.get_or_404(appointment_id)
    if request.method == 'POST':
        appointment.status = request.form['status']
        appointment.notes = request.form['notes']
        db.session.commit()
        flash('Appointment updated successfully!', 'success')
        return redirect(url_for('doctor.appointments'))

    return render_template('doctors/edit_appointment.html', appointment=appointment)


@bp.route('/reschedule_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def reschedule_appointment(appointment_id):
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    appointment = Appointment.query.get_or_404(appointment_id)
    if request.method == 'POST':
        appointment.appointment_date = datetime.strptime(request.form['new_date'], '%Y-%m-%d').date()
        appointment.appointment_time = datetime.strptime(request.form['new_time'], '%H:%M').time()
        db.session.commit()
        flash('Appointment rescheduled successfully!', 'success')
        return redirect(url_for('doctor.appointments'))

    return render_template('doctors/reschedule_appointment.html', appointment=appointment)


@bp.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    appointment = Appointment.query.get_or_404(appointment_id)
    try:
        appointment.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling appointment: {str(e)}', 'danger')

    return redirect(url_for('doctor.appointments'))

@bp.route('/update_status/<int:appointment_id>/<status>', methods=['POST'])
def update_status(appointment_id, status):
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = status
    db.session.commit()

    return redirect(url_for('doctor.appointments'))
#<-------------------------- messages -------------------------------->

# app/routes/doctor.py

@bp.route('/messages', methods=['GET'])
def messages():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    firebase_user_id = session.get('user_id')
    account = Account.query.filter_by(id=firebase_user_id).first()

    if not account:
        return redirect(url_for('auth.signin'))

    doctor_id = account.doctor_id
    all_clients = ClientAccounts.query.all()

    # Retrieve messages based on doctor_id
    messages_sent = Message.query.filter_by(sender_id=firebase_user_id).all()
    messages_received = Message.query.filter_by(recipient_id=firebase_user_id).all()

    client_ids = set([msg.recipient_id for msg in messages_sent] + [msg.sender_id for msg in messages_received])
    unique_clients = {}

    for client_id in client_ids:
        client = ClientAccounts.query.filter_by(client_id=client_id).first()
        if client:
            last_message = Message.query.filter(
                or_(
                    and_(Message.sender_id == firebase_user_id, Message.recipient_id == client_id),
                    and_(Message.sender_id == client_id, Message.recipient_id == firebase_user_id)
                )
            ).order_by(Message.timestamp.desc()).first()

            if last_message:
                unique_clients[client.client_id] = {
                    'client_name': f"{client.first_name} {client.last_name}",
                    'last_message': last_message.body,
                    'timestamp': last_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }

    # Mark all unread messages as read
    unread_messages = Message.query.filter_by(recipient_id=firebase_user_id, is_read=False).all()
    for message in unread_messages:
        message.is_read = True

    # Mark all unread notifications as read for this doctor
    unread_notifications = Notification.query.filter_by(doctor_id=doctor_id, is_read=False).all()
    for notification in unread_notifications:
        notification.is_read = True

    db.session.commit()  # Commit changes to update the read status

    unique_clients_list = [{'client_id': k, **v} for k, v in unique_clients.items()]
    return render_template('doctors/messages.html', all_clients=all_clients, unique_clients=unique_clients_list)



@bp.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        sender_id = session.get('user_id')
        receiver_id = data.get('client_id')
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
        
        # Create a notification for the new message
        new_notification = Notification(
            doctor_id=sender_id, 
            patient_id=receiver_id,
            message=f"New message from your patient: {body}",
            notification_type='message',
            timestamp=timestamp,
            is_read=False
        )
        db.session.add(new_notification)
        db.session.commit()
        
        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/get_messages', methods=['GET'])
def get_messages():
    sender_id = session.get('user_id')
    receiver_id = request.args.get('client_id')

    if not sender_id or not receiver_id:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    messages = Message.query.filter(
        (Message.sender_id == sender_id) & (Message.recipient_id == receiver_id) |
        (Message.sender_id == receiver_id) & (Message.recipient_id == sender_id)
    ).order_by(Message.timestamp.asc()).all()

    conversation = [{
        'sender': 'You' if msg.sender_id == sender_id else 'Client',
        'message': msg.body,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in messages]

    return jsonify({'success': True, 'conversation': conversation}), 200


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


#<---------------------- Patients ----------------------->
@bp.route('/patients', methods=['GET', 'POST'])
def patients():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    # Retrieve the doctor ID from the session
    doctor_id = session.get('user_id')
    doctor_account = Account.query.filter_by(id=doctor_id).first()
    if not doctor_account:
        flash('Doctor account not found!', 'danger')
        return redirect(url_for('auth.signin'))

    doctor_id = doctor_account.doctor_id

    # Extract search and filter parameters from the query string
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    # Query patients who have completed appointments with the logged-in doctor
    patients_query = db.session.query(ClientAccounts, Appointment).join(
        Appointment, ClientAccounts.client_id == Appointment.client_id
    ).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == 'Completed'  # Filter for completed appointments
    )

    if search_query:
        patients_query = patients_query.filter(
            or_(
                ClientAccounts.first_name.ilike(f'%{search_query}%'),
                ClientAccounts.last_name.ilike(f'%{search_query}%'),
                ClientAccounts.email.ilike(f'%{search_query}%')
            )
        )

    if status_filter:
        patients_query = patients_query.filter(Appointment.status == status_filter)

    # Implement pagination for the patient list
    pagination = patients_query.paginate(page=page, per_page=7)

    return render_template(
        'doctors/patients.html',
        patients=pagination.items,
        pagination=pagination,
        search_query=search_query,
        status_filter=status_filter
    )

@bp.route('/edit_patient/<string:client_id>', methods=['GET', 'POST'])
def edit_patient(client_id):
    # Query patient data
    patient = ClientAccounts.query.get_or_404(client_id)
    if request.method == 'POST':
        # Update patient information based on form submission
        patient.first_name = request.form['first_name']
        patient.last_name = request.form['last_name']
        patient.phone_number = request.form['phone_number']
        patient.address = request.form['address']
        patient.type = request.form['status']
        
        db.session.commit()
        flash('Patient information updated successfully!', 'success')
        return redirect(url_for('doctor.patients'))

    return render_template('doctors/edit_patient.html', patient=patient)

@bp.route('/update_patient_status/<string:client_id>/<string:status>', methods=['POST'])
def update_patient_status(client_id, status):
    # Query patient data
    patient = ClientAccounts.query.get_or_404(client_id)
    # Update patient status
    patient.type = status
    db.session.commit()
    flash('Patient status updated successfully.', 'success')
    return redirect(url_for('doctor.patients'))

@bp.route('/patient_profile/<string:client_id>', methods=['GET', 'POST'])
def patient_profile(client_id):
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    # Fetch the patient data using the client_id
    client_account = ClientAccounts.query.filter_by(client_id=client_id).first()
    patient = Patient.query.filter_by(patient_id=client_id).first()
    appointment = Appointment.query.filter_by(client_id=client_id, status='Completed').first()  # Check for completed status

    if not client_account or not appointment:
        flash('Patient not found or appointment not completed.', 'danger')
        return redirect(url_for('doctor.patients'))
    
    if not client_account or not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('doctor.patients'))

    if request.method == 'POST':
        # Update patient details
        client_account.first_name = request.form['first_name']
        client_account.last_name = request.form['last_name']
        client_account.email = request.form['email']
        client_account.phone_number = request.form['phone_number']
        patient.dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
        patient.insurance_number = request.form['insurance_number']
        patient.gender = request.form['gender']
        patient.doctor_id = request.form['doctor_id']

        db.session.commit()
        flash('Patient information updated successfully.', 'success')
        return redirect(url_for('doctor.patient_profile', client_id=client_id))

    doctors = Doctor.query.all()

    return render_template('doctors/patient_profile.html', client_account=client_account, patient=patient, doctors=doctors)



#<----------------------Reports----------------------->

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/reports', methods=['GET', 'POST'])
def reports():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    firebase_user_id = session.get('user_id')
    account = Account.query.filter_by(id=firebase_user_id).first()

    if not account:
        flash('Doctor account not found', 'error')
        return redirect(url_for('auth.signin'))

    doctor_id = account.doctor_id
    completed_appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='Completed').all()

    # Fetch existing reports with patient and test details
    reports = db.session.query(LabResult, ClientAccounts, LabTest).join(ClientAccounts, LabResult.patient_id == ClientAccounts.client_id).join(LabTest, LabResult.test_id == LabTest.test_id).filter(LabResult.doctor_id == doctor_id).all()

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        test_id = request.form.get('test_id')
        result_value = request.form.get('result_value')
        result_date = datetime.strptime(request.form.get('result_date'), '%Y-%m-%d')
        notes = request.form.get('notes')
        report_type = request.form.get('report_type')

        # Handle image upload
        image_path = None
        if report_type == 'imaging' and 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
                
                # Update path to use forward slashes and make it relative to 'static'
                image_path = os.path.relpath(image_path, start='app/static').replace("\\", "/")
                print(f"Image saved to: {image_path}")  # Debugging log

        # Add new report to the database
        new_report = LabResult(
            patient_id=patient_id,
            doctor_id=doctor_id,
            test_id=test_id,
            result_value=result_value,
            result_date=result_date,
            notes=notes,
            image_path=image_path  # Store the image path if applicable
        )
        db.session.add(new_report)
        db.session.commit()
        flash('Medical report added successfully!', 'success')
        return redirect(url_for('doctor.reports'))

    return render_template('doctors/reports.html', completed_appointments=completed_appointments, reports=reports)


#<----------------------Lab Results----------------------->
# Predefined lab tests
PREDEFINED_TESTS = [
    {"name": "Blood Test", "description": "A test to assess general health or detect specific conditions."},
    {"name": "Urine Test", "description": "A test to detect substances in the urine and assess health."},
    {"name": "Thyroid Function Tests", "description": "A test to evaluate thyroid gland function."},
    {"name": "Liver Function Test", "description": "A test to check the health of the liver."},
    {"name": "Complete Blood Count (CBC)", "description": "A test that provides information about red and white blood cells."},
    # Add more predefined tests as needed
]

@bp.route('/lab_results', methods=['GET', 'POST'])
def lab_results():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    firebase_user_id = session.get('user_id')
    account = Account.query.filter_by(id=firebase_user_id).first()

    if not account:
        flash('Doctor account not found', 'error')
        return redirect(url_for('auth.signin'))

    doctor_id = account.doctor_id

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        test_id = request.form.get('test_id')
        other_test_name = request.form.get('other_test_name')
        result_value = request.form.get('result_value')
        result_date = request.form.get('result_date')
        notes = request.form.get('notes')
        upload_file = request.files.get('upload_file')

        try:
            # Handle file upload
            image_path = None
            if upload_file and allowed_file(upload_file.filename):
                filename = secure_filename(upload_file.filename)
                upload_folder = os.path.join('app', 'static', 'uploads', 'lab_results')
                os.makedirs(upload_folder, exist_ok=True)
                image_path = os.path.join(upload_folder, filename)
                upload_file.save(image_path)

                # Ensure correct path formatting
                image_path = os.path.relpath(image_path, start='app/static').replace("\\", "/")
                print(f"Image saved to: {image_path}")  # Debugging log

            # Determine the test description and ID
            if test_id == 'other' and other_test_name:
                # Use the AI model to generate the description for the new test
                test_description = get_ai_generated_description(other_test_name)

                # Create a new LabTest entry
                new_test = LabTest(
                    test_name=other_test_name,
                    description=test_description
                )
                db.session.add(new_test)
                db.session.commit()
                test_id = new_test.test_id
            else:
                # Use the predefined test description
                predefined_test = LabTest.query.filter_by(test_id=test_id).first()
                if not predefined_test:
                    # Create a new entry if it doesn't exist in the database
                    for test in PREDEFINED_TESTS:
                        if test['name'] == test_id:
                            new_test = LabTest(
                                test_name=test['name'],
                                description=test['description']
                            )
                            db.session.add(new_test)
                            db.session.commit()
                            test_id = new_test.test_id
                            break

            # Add Lab Result
            lab_result = LabResult(
                patient_id=patient_id,
                doctor_id=doctor_id,
                test_id=test_id,
                result_value=result_value,
                result_date=datetime.strptime(result_date, '%Y-%m-%d').date(),
                notes=notes,
                image_path=image_path
            )
            db.session.add(lab_result)
            db.session.commit()

            flash('Lab result added successfully!', 'success')
            return redirect(url_for('doctor.lab_results'))
        except Exception as e:
            db.session.rollback()  # Rollback the session in case of an error
            flash(f"An error occurred: {str(e)}", 'error')
            return redirect(url_for('doctor.lab_results'))

    # Fetch all tests and patients for the dropdown
    tests = LabTest.query.all() + [LabTest(test_id=test['name'], test_name=test['name'], description=test['description']) for test in PREDEFINED_TESTS]

    # Get patients with completed appointments who do not have lab results yet
    patients_with_results = db.session.query(LabResult.patient_id).filter_by(doctor_id=doctor_id).distinct()
    patients = ClientAccounts.query.join(Appointment, ClientAccounts.client_id == Appointment.client_id)\
        .filter(Appointment.status == 'Completed', Appointment.doctor_id == doctor_id)\
        .filter(~ClientAccounts.client_id.in_(patients_with_results)).all()

    # Pagination setup
    page = request.args.get('page', 1, type=int)
    lab_results_pagination = LabResult.query.filter_by(doctor_id=doctor_id).order_by(LabResult.result_date.desc()).paginate(page=page, per_page=10)
    lab_results = lab_results_pagination.items

    return render_template('doctors/lab_results.html', tests=tests, patients=patients, lab_results=lab_results, pagination=lab_results_pagination)

def get_ai_generated_description(test_name):
    # Ensure test_name is provided
    if test_name:
        try:
            # Configure the genai client with the API key from environment variables
            genai.configure(api_key=os.environ['GOOGLE_API_KEY1'])
            
            # Initialize the GenerativeModel
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Construct the AI prompt
            ai_prompt = f"Give me a short description of the medical defination called {test_name}."
            
            # Generate the description
            response = model.generate_content(ai_prompt)
            
            # Extract and clean up the response text
            enhanced_notes = response.text.strip() if response.text else "No description available."
        
        except Exception as e:
            # Handle any errors that occur during the API call
            enhanced_notes = f"Error generating description: {str(e)}"
    else:
        enhanced_notes = "No description available."
    
    return enhanced_notes

@bp.route('/add_lab_test', methods=['POST'])
def add_lab_test():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    # Get form data
    test_name = request.form.get('test_name')
    description = request.form.get('description')

    # Check if the test name is not empty
    if not test_name:
        flash('Test name is required.', 'error')
        return redirect(url_for('doctor.lab_results'))

    try:
        # Create a new LabTest object
        new_lab_test = LabTest(
            test_name=test_name,
            description=description
        )

        # Add and commit the new lab test to the database
        db.session.add(new_lab_test)
        db.session.commit()

        flash('Lab test type added successfully!', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback the session in case of an error
        flash(f"An error occurred: {str(e)}", 'error')

    return redirect(url_for('doctor.lab_results'))

#<----------------------prescription and medical history----------------------->
@bp.route('/prescription', methods=['GET', 'POST'])
def prescription():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')
        appointment_id = request.form.get('appointment_id')
        
        new_prescription = Prescription(
            patient_id=patient_id,
            doctor_id=session.get('user_id'),
            appointment_id=appointment_id,
            prescription=prescription,
            notes=notes
        )
        db.session.add(new_prescription)
        db.session.commit()
        
        flash('Prescription added successfully!', 'success')
        return redirect(url_for('doctor.prescription'))
    
    return render_template('doctors/prescription.html')


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
def settings():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    return render_template('doctors/settings.html')

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

#<----------------------Dashboard Navbar----------------------->
@bp.route('/patient-records')
def patient_records():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))
    return render_template('doctors/patient_records.html')

@bp.route('/clinical-reports')
def clinical_reports():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))
    return render_template('doctors/clinical_reports.html')

@bp.route('/ai-diagnostics')
def ai_diagnostics():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))
    return render_template('doctors/ai_diagnostics.html')

@bp.route('/healthcare-insights')
def healthcare_insights():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))
    return render_template('doctors/healthcare_insights.html')

@bp.route('/profile')
def profile():
    if 'user' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('auth.signin'))
    return render_template('doctors/profile.html')

@bp.route('/notifications')
def notifications():
    if 'user' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('auth.signin'))
    return render_template('doctors/notifications.html')