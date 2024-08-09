import os
from flask import Blueprint, flash, json, jsonify, render_template, request, send_from_directory, session, redirect, url_for
import json
from ..models_db import BloodTest, LabResult, LabTest, Patient, Doctor, Appointment, Message, Prescription, Settings, User, Account, ClientAccounts, Notification
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
from firebase_admin import auth as firebase_auth
from werkzeug.security import generate_password_hash, check_password_hash

# Define a folder where uploaded images will be stored
UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads', 'lab_results')
UPLOAD_FOLDER_PROF = os.path.join('app', 'static', 'uploads', 'profile_pictures')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_PROF, exist_ok=True)


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


#<---------------------- Doctor Profile ----------------------->
@bp.route('/dashboard/doctors', methods=['GET'])
def doctors():
    doctor_name = request.args.get('doctor_name', '').strip()
    specialization = request.args.get('specialization', 'All')
    status = request.args.get('status', 'All').lower()  # Convert to lowercase
    
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10  # Number of items per page
    
    query = Doctor.query
    
    if doctor_name:
        query = query.filter(Doctor.first_name.ilike(f'{doctor_name}%'))

    if specialization and specialization != "All":
        query = query.filter(Doctor.specialization == specialization)

    if status and status != "all":
        query = query.filter(Doctor.status.ilike(f'%{status}%'))

    total = query.count()
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    doctors = pagination.items
    
    specializations = [s.specialization for s in Doctor.query.with_entities(Doctor.specialization).distinct()]
    
    return render_template('doctors/doctors.html', doctors=doctors, specialization_filter=specialization, status_filter=status, pagination=pagination, specializations=specializations)



@bp.route('/dashboard/doctors/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor_data = {
        'first_name': doctor.first_name,
        'last_name': doctor.last_name,
        'specialization': doctor.specialization,
        'status': doctor.status,
        'schedule': doctor.schedule
    }
    return jsonify(doctor_data)


@bp.route('/urine_test')
def urine_test():
    return render_template('doctors/urine_test.html')

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
    patients_query = db.session.query(ClientAccounts, Appointment, Patient).join(
        Appointment, ClientAccounts.client_id == Appointment.client_id
    ).join(
        Patient, ClientAccounts.client_id == Patient.patient_id
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

    # Calculate the patient's age
    patients = []
    for client_account, appointment, patient in patients_query.all():
        # Calculate age
        today = datetime.now().date()
        if patient.dob:
            age = today.year - patient.dob.year - ((today.month, today.day) < (patient.dob.month, patient.dob.day))
        else:
            age = 'N/A'  # Use 'N/A' when DOB is not available

        # Append the patient data with age
        patients.append((client_account, appointment, patient, age))

    # Implement pagination for the patient list
    pagination = patients_query.paginate(page=page, per_page=7)

    return render_template(
        'doctors/patients.html',
        patients=patients,  # Use the new patients list with age
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


# @bp.route('/lab_results', methods=['GET', 'POST'])
# def lab_results():
#     if 'user' not in session or session.get('user_type') != 'doctors':
#         return redirect(url_for('auth.signin'))

#     firebase_user_id = session.get('user_id')
#     account = Account.query.filter_by(id=firebase_user_id).first()
#     print("account", account)
#     if not account:
#         flash('Doctor account not found', 'error')
#         return redirect(url_for('auth.signin'))

#     doctor_id = account.doctor_id
#     print("doctor_id", doctor_id)

#     # Fetch lab results for the doctor based on lab_doctor_id (from Account.id)
#     lab_doctor_id = account.id
#     print("lab_doctor_id: ", lab_doctor_id)

#     # Fetch lab results where the doctor_id matches and patient_id corresponds to client_id
#     lab_results = db.session.query(BloodTest).join(ClientAccounts, BloodTest.patient_id == ClientAccounts.client_id).filter(
#         BloodTest.doctor_id == lab_doctor_id
#     ).all()

#     # For debugging, print out the patient information
#     # for result in lab_results:
#     #     print("Patient Info:", result.patient.first_name, result.patient.last_name)

#     # Pagination parameters
#     page = request.args.get('page', 1, type=int)
#     per_page = 5
#     # pagination = db.paginate(page=page, per_page=per_page, error_out=False, items=lab_results)
#     # patients = pagination.items

#     return render_template('doctors/lab_results.html', patients=patients, lab_results=lab_results)

@bp.route('/lab_results', methods=['GET', 'POST'])
def lab_results():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    firebase_user_id = session.get('user_id')
    account = Account.query.filter_by(id=firebase_user_id).first()
    print("account", account)
    if not account:
        flash('Doctor account not found', 'error')
        return redirect(url_for('auth.signin'))

    doctor_id = account.doctor_id
    print("doctor_id", doctor_id)
    # Fetch patients with completed appointments
    patients_query = db.session.query(ClientAccounts).join(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == 'Completed'
    )
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 5
    pagination = patients_query.paginate(page=page, per_page=per_page, error_out=False)
    patients = pagination.items

    # Fetch lab results for the doctor
    lab_doctor_id = account.id
    print("lab_doctor_id: ", lab_doctor_id)
    lab_results = BloodTest.query.filter_by(doctor_id=lab_doctor_id).all()
    
    return render_template('doctors/lab_results.html', patients=patients, lab_results=lab_results, pagination=pagination)



@bp.route('/test_form', methods=['GET', 'POST'])
def test_form():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    if request.method == 'POST':
        doctor_id = session['user_id']
        patient_id = request.form['patient_id']
        test_type = request.form['test_type']

        # Get the form data as JSON
        test_data = request.form.to_dict()
        test_data.pop('patient_id')
        test_data.pop('test_type')

        # Save the test data in the database
        new_test = BloodTest(
            patient_id=patient_id,
            doctor_id=doctor_id,
            test_type=test_type,
            results=test_data
        )
        db.session.add(new_test)
        db.session.commit()

        flash('Test results saved successfully!', 'success')
        return redirect(url_for('doctor.lab_results'))

    patient_id = request.args.get('patient_id')
    test_type = request.args.get('test_type')

    return render_template('doctors/test_form.html', patient_id=patient_id, test_type=test_type)


@bp.route('/view_lab_result/<int:result_id>', methods=['GET'])
def view_lab_result(result_id):
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    lab_result = BloodTest.query.get(result_id)
    if not lab_result:
        flash('Lab result not found', 'error')
        return redirect(url_for('doctor.lab_results'))

    return render_template('doctors/view_lab_result.html', lab_result=lab_result)


@bp.route('/edit_lab_result/<int:result_id>', methods=['GET', 'POST'])
def edit_lab_result(result_id):
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    lab_result = BloodTest.query.get(result_id)
    if not lab_result:
        flash('Lab result not found', 'error')
        return redirect(url_for('doctor.lab_results'))

    if request.method == 'POST':
        test_data = request.form.to_dict()
        lab_result.results = test_data
        db.session.commit()
        flash('Test results updated successfully!', 'success')
        return redirect(url_for('doctor.lab_results'))

    return render_template('doctors/edit_lab_result.html', lab_result=lab_result)





#<----------------------prescription and medical history----------------------->
@bp.route('/prescription', methods=['GET', 'POST'])
def prescription():
    if 'user' not in session or session.get('user_type') != 'doctors':
        return redirect(url_for('auth.signin'))

    firebase_user_id = session.get('user_id')
    account = Account.query.filter_by(id=firebase_user_id).first()
    
    if not account:
        flash('Doctor account not found', 'error')
        return redirect(url_for('auth.signin'))

    doctor_id = account.doctor_id

    # Fetch completed appointments with patient details
    completed_appointments = (
        db.session.query(Appointment)
        .filter_by(doctor_id=doctor_id, status='Completed')
        .join(ClientAccounts, Appointment.client_id == ClientAccounts.client_id)
        .all()
    )
    print("completed_appointments", completed_appointments)
    
    # Handle form submission for creating a prescription
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        medication_id = request.form.get('medication')  # Ensure this fetches the medication_id correctly
        dosage = request.form.get('dosage')
        frequency = request.form.get('frequency')
        duration = request.form.get('duration')

        try:
            # Parse start and end dates
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=int(duration.split()[0]))  # Assuming '7 days'

            # Create and add a new prescription to the database
            prescription = Prescription(
                doctor_id=doctor_id,
                patient_id=patient_id,
                medication_id=medication_id,
                dosage=dosage,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(prescription)
            db.session.commit()
            flash('Prescription created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating prescription: {str(e)}', 'danger')
        return redirect(url_for('doctor.prescription'))

    # Fetch all prescriptions for this doctor to display
    prescriptions = (
        db.session.query(Prescription)
        .filter_by(doctor_id=doctor_id)
        .all()
    )

    return render_template('doctors/prescription.html', completed_appointments=completed_appointments, prescriptions=prescriptions)


#<----------------------monitor----------------------->

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



@bp.route('/notifications')
def notifications():
    if 'user' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('auth.signin'))
    return render_template('doctors/notifications.html')


#<---------------------- settings ----------------------->

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('auth.signin'))

    user_id = session['user_id']
    print("user_id: ", user_id)
    user = Account.query.get(user_id)
    print("user: ", user)
    doctor_info = Doctor.query.get(user.doctor_id)
    user_local = User.query.filter_by(email=user.email).first()

    if request.method == 'POST':
        form_name = request.form.get('form_name')

        if form_name == 'personal_info':
            doctor_info.first_name = request.form.get('first_name')
            doctor_info.last_name = request.form.get('last_name')
            doctor_info.dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date()
            doctor_info.gender = request.form.get('gender')

            user_local.username = f"{doctor_info.first_name} {doctor_info.last_name}"

            if 'profile_picture' in request.files:
                profile_picture = request.files['profile_picture']
                if profile_picture and allowed_file(profile_picture.filename):
                    filename = secure_filename(profile_picture.filename)
                    image_path = os.path.join(UPLOAD_FOLDER_PROF, filename)
                    profile_picture.save(image_path)
                    doctor_info.image_path = os.path.relpath(image_path, start='app/static').replace("\\", "/")

            db.session.commit()
            flash('Personal information updated successfully!', 'success')

        elif form_name == 'contact_details':
            doctor_info.phone_number = request.form.get('phone')
            doctor_info.address = request.form.get('address')
            db.session.commit()
            flash('Contact details updated successfully!', 'success')

        elif form_name == 'preferences':
            user_local.language = request.form.get('language')
            user_local.timezone = request.form.get('timezone')
            user_local.email_notifications = 'email_notifications' in request.form
            user_local.sms_notifications = 'sms_notifications' in request.form
            db.session.commit()
            flash('Preferences updated successfully!', 'success')

        elif form_name == 'security_settings':
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if not check_password_hash(user.password, current_password):
                flash('Current password is incorrect', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match', 'danger')
            else:
                try:
                    # Update password in Firebase
                    firebase_auth.update_user(user_id, password=new_password)    
                                    
                    # Hash the new password and update local database
                    hashed_password = generate_password_hash(new_password)
                    user.password = hashed_password
                    user.plain_password = hashed_password
                    db.session.commit()
                    
                    flash('Password updated successfully!', 'success')
                except Exception as e:
                    flash(f'Error updating password: {e}', 'danger')

    return render_template('doctors/settings.html', user=user, doctor_info=doctor_info, user_local=user_local)
