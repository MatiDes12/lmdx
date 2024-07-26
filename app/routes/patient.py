
from mailbox import Message
from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Appointment, Medication, Reminder, User, Message
from .. import sqlalchemy_db as db
from datetime import datetime, timedelta
from app.routes.auth import firebase_db

bp = Blueprint('patient', __name__)


#<-------------------------- dashboard -------------------------------->

@bp.route('/dashboard')
def dashboard():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    id_token = session.get('user_id_token')  # Also ensure that the Firebase ID token is stored in session
    
    try:
        # Fetch user data from Firebase
        user_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
        if user_data:
            print('test')
            first_name = user_data.get('first_name')
            last_name = user_data.get('last_name')
            return render_template('clients/dashboard.html', first_name=first_name, last_name=last_name)
        else:
            flash('Unable to fetch user details.', 'error')
            return redirect(url_for('auth.signin'))
    except Exception as e:
        flash('Error accessing user information.', 'error')
        print(f"Firebase fetch error: {e}")
        return redirect(url_for('auth.signin'))
    
# @bp.route('/fetch_user_info')
# def fetch_user_info():
#     try:
#         user_id = session.get('user_id')
#         if not user_id:
#             raise ValueError("User ID not found in session")

#         user_info = User.query.filter_by(id=user_id).first()
#         if not user_info:
#             raise ValueError("No user found with the given ID")

#         return render_template('user_info.html', user=user_info)

#     except Exception as e:
#         # Log the error for further investigation
#         print(f"Error accessing user information: {e}")
#         flash('Error accessing user information.', 'error')
#         return redirect(url_for('auth.login'))  # Redirect to login or appropriate error page


#<-------------------------- appointments -------------------------------->
@bp.route('/appointments', methods=['GET', 'POST'])
def appointments():
    # Fetch upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.now(),
        Appointment.status != 'Cancelled'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

    # Fetch all doctors
    doctors = Doctor.query.all()

    # Generate available times (example: 9 AM to 5 PM, every 30 minutes)
    start_time = datetime.strptime("09:00", "%H:%M")
    end_time = datetime.strptime("17:00", "%H:%M")
    available_times = []
    while start_time <= end_time:
        available_times.append(start_time.strftime("%I:%M %p"))
        start_time += timedelta(minutes=30)

    if request.method == 'POST':
        # Handle appointment booking
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        patient_id = 1  # Replace with actual patient ID (you may want to get this from the session)
        
        # Create new appointment
        new_appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=datetime.strptime(appointment_date, "%Y-%m-%d").date(),
            appointment_time=datetime.strptime(appointment_time, "%I:%M %p").time(),
            status='Scheduled'
        )
        db.session.add(new_appointment)
        db.session.commit()

        return redirect(url_for('patient.appointments'))

    return render_template('clients/appointments.html', 
                           upcoming_appointments=upcoming_appointments,
                           doctors=doctors,
                           available_times=available_times)
    

@bp.route('/make_appointment', methods=['POST'])
def make_appointment():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    doctor_id = request.form.get('doctor_id')
    date = request.form.get('date')
    time = request.form.get('time')
    notes = request.form.get('notes', '')
    
    if not all([doctor_id, date, time]):
        flash('All fields are required.', 'error')
        return redirect(url_for('patient.appointments'))

    appointment_date = datetime.strptime(date, '%Y-%m-%d')
    appointment_time = datetime.strptime(time, '%H:%M').time()
    
    try:
        new_appointment = Appointment(
            patient_id=user_id,
            doctor_id=doctor_id,
            date=appointment_date,
            time=appointment_time,
            status='Scheduled',
            notes=notes
        )
        db.session.add(new_appointment)
        db.session.commit()
        flash('Appointment made successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error making appointment.', 'error')
        print(f"Appointment creation error: {e}")
    
    return redirect(url_for('patient.dashboard'))


#<-------------------------- messages -------------------------------->

@bp.route('/messages', methods=['GET'])
def messages():
    if 'user' not in session or session.get('user_type') not in ['patient', 'client']:
        return redirect(url_for('auth.signin'))

    # Fetch doctors
    doctors = Doctor.query.all()
    doctor_statuses = []
    for doctor in doctors:
        user = User.query.get(doctor.doctor_id)
        status = 'Active' if user else 'Inactive'
        doctor_statuses.append({
            'id': doctor.doctor_id,
            'name': f"{doctor.first_name} {doctor.last_name}",
            'specialization': doctor.specialization,
            'status': status
        })

    # Fetch messages sent to the current client from doctors
    client_id = session.get('user_id')
    messages = Message.query.filter_by(recipient_id=client_id).all()
    message_details = []

    # Fetch the sender information for each message and ensure timestamp is a datetime object
    for message in messages:
        sender = User.query.get(message.sender_id)
        doctor = Doctor.query.filter_by(doctor_id=sender.doctor_id).first()
        if doctor:
            timestamp = message.timestamp
            if isinstance(timestamp, str):
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
            message_details.append({
                'doctor_name': f"{doctor.first_name} {doctor.last_name}",
                'doctor_image': f"https://i.pravatar.cc/300?img={doctor.doctor_id % 70}",  # Random image for doctor
                'body': message.body,
                'timestamp': timestamp
            })

    return render_template('clients/messages.html', doctor_statuses=doctor_statuses, doctors=doctors, messages=message_details)

@bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user' not in session or session.get('user_type') not in ['patient', 'client']:
        return redirect(url_for('auth.signin'))

    doctor_id = request.form.get('doctor_id')
    message_body = request.form.get('message')
    sender_id = session.get('user_id')  # Assuming you store the logged-in user's ID in session

    if not doctor_id or not message_body:
        flash('Please select a doctor and enter a message.')
        return redirect(url_for('patient.messages'))

    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        flash('Invalid doctor selected.')
        return redirect(url_for('patient.messages'))

    recipient_id = doctor.doctor_id

    # Create and save the message
    message = Message(sender_id=sender_id, recipient_id=recipient_id, subject='Message from Client', body=message_body)
    db.session.add(message)
    db.session.commit()

    flash('Message sent successfully.')
    return redirect(url_for('patient.messages'))


@bp.route('/active_doctors', methods=['GET'])
def active_doctors():
    if 'user' not in session or session.get('user_type') not in ['patient', 'client']:
        return redirect(url_for('auth.signin'))

    # Fetch only 5 active doctors
    doctors = Doctor.query.join(User).filter(User.is_active == True).limit(5).all()
    doctor_details = []
    for index, doctor in enumerate(doctors):
        user = User.query.get(doctor.doctor_id)
        doctor_details.append({
            'id': doctor.doctor_id,
            'name': f"{doctor.first_name} {doctor.last_name}",
            'specialization': doctor.specialization,
            'status': 'Active',
            'image_url': f"https://i.pravatar.cc/30{index+1}"  # Generates a unique profile image for each doctor
        })

    return render_template('active_doctors.html', doctors=doctor_details)




#<-------------------------- pretty date -------------------------------->
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc.
    """
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now

    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff // 30) + " months ago"
    return str(day_diff // 365) + " years ago"


#<-------------------------- test results -------------------------------->

@bp.route('/test_results')
def test_results():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    return render_template('clients/test_results.html')

#<-------------------------- medication -------------------------------->
@bp.route('/medication', methods=['GET', 'POST'])
def medication():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    if request.method == 'POST':
        medication_id = request.form.get('medication_id')
        reminder_time = request.form.get('reminder_time')
        
        new_reminder = Reminder(medication_id=medication_id, time=datetime.strptime(reminder_time, "%H:%M").time())
        db.session.add(new_reminder)
        db.session.commit()
        return redirect(url_for('patient.medication'))
    
    medications = Medication.query.all()
    today_reminders = Reminder.query.filter(Reminder.time >= datetime.now().time()).all()
    return render_template('clients/medication.html', medications=medications, today_reminders=today_reminders)

@bp.route('/set_reminder', methods=['POST'])
def set_reminder():
    medication_id = request.form.get('medication_id')
    reminder_time = request.form.get('reminder_time')
    
    new_reminder = Reminder(medication_id=medication_id, time=datetime.strptime(reminder_time, "%H:%M").time())
    db.session.add(new_reminder)
    db.session.commit()
    
    return redirect(url_for('patient.medication'))

#<-------------------------- visits -------------------------------->
@bp.route('/visits')
def visits():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    # Fetch visit history, latest visit details, and follow-up actions from the database
    visits = [
        {"date": datetime(2024, 7, 15), "doctor_name": "Dr. John Smith", "summary": "Routine check-up, recommended vitamin D supplementation.", "next_steps": "Follow-up in 3 months."},
        {"date": datetime(2024, 10, 20), "doctor_name": "Dr. Jane Doe", "summary": "Follow-up visit, improved health markers.", "next_steps": "Annual check-up scheduled for next year."},
        {"date": datetime(2025, 1, 10), "doctor_name": "Dr. John Smith", "summary": "Discussing long-term treatment options for chronic conditions.", "next_steps": "Review new medications in 6 months."}
    ]
    
    latest_visit = {
        "symptoms": ["Fatigue", "Joint pain", "Occasional headaches"],
        "medications": [
            {"name": "Vitamin D", "action": "New prescription", "action_color": "green"},
            {"name": "Ibuprofen", "action": "Dosage increased", "action_color": "yellow"},
            {"name": "Allergy medication", "action": "Discontinued", "action_color": "red"}
        ],
        "notes": "Patient shows improvement in overall health markers. Recommended lifestyle changes appear to be effective. Continue monitoring and adjust treatment plan as needed."
    }
    
    follow_up_actions = [
        {"title": "Blood Test", "description": "Schedule a follow-up blood test in 2 weeks", "action_text": "Schedule Now"},
        {"title": "Specialist Referral", "description": "Book an appointment with a rheumatologist", "action_text": "Find Specialist"},
        {"title": "Medication Review", "description": "Review effectiveness of new prescriptions in 1 month", "action_text": "Set Reminder"}
    ]
    
    return render_template('clients/visits.html', visits=visits, latest_visit=latest_visit, follow_up_actions=follow_up_actions)

# @bp.route('/view_details/<int:visit_id>')
# def view_details(visit_id):
#     visit = Visit.query.get_or_404(visit_id)
#     return render_template('view_details.html', visit=visit)

# @bp.route('/schedule_now')
# def schedule_now():
#     # Logic to schedule a blood test
#     return redirect(url_for('visit_summary'))

# @bp.route('/find_specialist')
# def find_specialist():
#     # Logic to find a specialist
#     return redirect(url_for('visit_summary'))

# @bp.route('/set_reminder', methods=['POST'])
# def set_reminder():
#     medication_id = request.form.get('medication_id')
#     reminder_time = request.form.get('reminder_time')
    
#     new_reminder = Reminder(medication_id=medication_id, time=datetime.strptime(reminder_time, "%H:%M").time())
#     db.session.add(new_reminder)
#     db.session.commit()
    
#     return redirect(url_for('visit_summary'))

#<-------------------------- billing -------------------------------->
@bp.route('/billing')
def billing():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    return render_template('clients/billing.html')


#<-------------------------- insurance -------------------------------->
@bp.route('/insurance')
def insurance():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    return render_template('clients/insurance.html')


#<-------------------------- health tips -------------------------------->

@bp.route('/health_tips')
def health_tips():
    tips = [
        "Stay hydrated by drinking at least 8 glasses of water a day.",
        "Exercise for at least 30 minutes most days of the week.",
        "Maintain a balanced diet rich in fruits, vegetables, and lean proteins.",
        "Get at least 7-8 hours of sleep per night to promote mental and physical health.",
        "Manage stress through mindfulness, meditation, or talking to a professional."
    ]
    return render_template('clients/health_tips.html', tips=tips)

