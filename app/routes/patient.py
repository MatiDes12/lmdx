
from mailbox import Message
from flask import Blueprint, jsonify, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Appointment, Medication, Reminder, User, Message, Patient
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
    


#<-------------------------- appointments -------------------------------->
def generate_available_times(doctor_id, appointment_date):
    doctor = Doctor.query.get(doctor_id)
    if not doctor or doctor.status != 'Active':
        print(f"Doctor {doctor_id} not active or not found.")
        return []

    working_hours = doctor.time.split(' - ')
    start_time = datetime.strptime(working_hours[0], "%I:%M %p")
    end_time = datetime.strptime(working_hours[1], "%I:%M %p")

    available_times = []
    while start_time < end_time:
        available_times.append(start_time.strftime("%I:%M %p"))
        start_time += timedelta(minutes=120) 

    # Debug: print all generated times before filtering
    print(f"Generated times for Doctor {doctor_id} on {appointment_date}: {available_times}")

    # Fetch booked times for the doctor on the given date
    booked_times = [appt.appointment_time.strftime("%I:%M %p") for appt in Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status == 'Scheduled'
    ).all()]

    print(f"Booked times for Doctor {doctor_id} on {appointment_date}: {booked_times}")

    # Filter out booked times
    available_times = [time for time in available_times if time not in booked_times]
    print("available_times: ",available_times)
    return available_times

@bp.route('/get-available-times', methods=['GET'])
def get_available_times():
    doctor_id = request.args.get('doctor_id')
    date = request.args.get('date')
    if doctor_id and date:
        available_times = generate_available_times(doctor_id, datetime.strptime(date, "%Y-%m-%d").date())
        return jsonify(available_times)
    return jsonify([])



@bp.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        reason = request.form.get('reason')
        notes = request.form.get('notes')
        client_id = session.get('user_id')

        if not client_id:
            flash('You must be logged in to schedule an appointment.')
            return redirect(url_for('auth.signin'))

        new_appointment = Appointment(
            client_id=client_id,
            doctor_id=doctor_id,
            appointment_date=datetime.strptime(appointment_date, "%Y-%m-%d").date(),
            appointment_time=datetime.strptime(appointment_time, "%I:%M %p").time(),
            status='Scheduled',
            reason=reason,
            notes=notes
        )
        db.session.add(new_appointment)
        db.session.commit()

        return redirect(url_for('patient.appointments'))

    doctors = Doctor.query.filter_by(status='Active').all()
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.now(),
        Appointment.status != 'Cancelled'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

    doctor_timeslots = {doctor.doctor_id: generate_available_times(doctor.doctor_id, datetime.now().date()) for doctor in doctors}
    
    print("Doctor timeslots: ", doctor_timeslots)
    return render_template('clients/appointments.html', 
                           upcoming_appointments=upcoming_appointments,
                           doctors=doctors,
                           doctor_timeslots=doctor_timeslots)

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


#<-------------------------- profile_settings -------------------------------->

# @bp.route('/profile_settings', methods=['GET', 'POST'])
# @login_required  # Ensure user is logged in
# def profile_settings():
#     user_id = current_user.user_id  # Assuming you have a way to get the current logged in user's ID
#     patient = Patient.query.filter_by(user_id=user_id).first()

#     if request.method == 'POST':
#         dob = request.form.get('dob')
#         insurance_number = request.form.get('insurance_number')
#         gender = request.form.get('gender')

#         # Validations can be added here
#         if dob:
#             patient.dob = datetime.strptime(dob, '%Y-%m-%d')  # Make sure the date format matches the input
#         if insurance_number:
#             patient.insurance_number = insurance_number
#         if gender:
#             patient.gender = gender

#         db.session.commit()
#         flash('Profile updated successfully!', 'success')
#         return redirect(url_for('profile_settings'))

#     return render_template('profile_settings.html', patient=patient)
