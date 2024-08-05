from mailbox import Message
import os
import random
import re
from flask import Blueprint, json, jsonify, render_template, redirect, url_for, session, request, flash
from ..models_db import ClientAccounts, Doctor, Appointment, FollowUpAction, Medication, Patient, Reminder, User, Message, Visit
from ..models_db import ClientAccounts, Doctor, Appointment, LabResult, LabTest, Medication, Patient, Reminder, User, Message
from flask import Blueprint, jsonify, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Account, Appointment, Medication, Reminder, User, Message, Notification
from .. import sqlalchemy_db as db
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app.routes.auth import firebase_db
import google.generativeai as genai
from dotenv import load_dotenv

from sqlalchemy import and_, or_

bp = Blueprint('patient', __name__)

# Load environment variables from .env file
load_dotenv()

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads', 'lab_results')
UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads', 'profile_pictures')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#<-------------------------- dashboard -------------------------------->

@bp.route('/dashboard')
def patient_dashboard():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))

    user_id = session.get('user_id')
    id_token = session.get('user_id_token')

    try:
        # Fetch user data from Firebase
        user_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
        if user_data:
            first_name = user_data.get('first_name')
            last_name = user_data.get('last_name')

            unread_messages_count = Message.query.filter_by(recipient_id=user_id, is_read=False).count()


            # Fetch unread notifications
            notifications = []
            notification_data = Notification.query.filter_by(patient_id=user_id, is_read=False).all()
            if notification_data:
                for notification in notification_data:
                    doctor = Doctor.query.get(notification.doctor_id)
                    notifications.append({
                        'user_name': doctor.first_name + " " + doctor.last_name if doctor else 'System',
                        'message': notification.message,
                        'time_ago': get_time_ago(notification.timestamp)
                    })
            
                    
            # Fetch today's and tomorrow's appointments
            today_date = datetime.now().date()
            tomorrow_date = today_date + timedelta(days=1)

            today_appointments = Appointment.query.filter_by(client_id=user_id, appointment_date=today_date, status='Scheduled').all()
            tomorrow_appointments = Appointment.query.filter_by(client_id=user_id, appointment_date=tomorrow_date, status='Scheduled').all()

            for appointment in today_appointments:
                doctor = Doctor.query.get(appointment.doctor_id)
                notifications.append({
                    'user_name': doctor.first_name + " " + doctor.last_name if doctor else 'Unknown Doctor',
                    'message': f"Upcoming appointment at {appointment.appointment_time.strftime('%I:%M %p')}",
                    'time_ago': 'Today'
                })

            for appointment in tomorrow_appointments:
                doctor = Doctor.query.get(appointment.doctor_id)
                notifications.append({
                    'user_name': doctor.first_name + " " + doctor.last_name if doctor else 'Unknown Doctor',
                    'message': f"Appointment tomorrow at {appointment.appointment_time.strftime('%I:%M %p')}",
                    'time_ago': 'Tomorrow'
                })

            return render_template('clients/dashboard.html', first_name=first_name, last_name=last_name, notifications=notifications, unread_messages_count=unread_messages_count)

        else:
            flash('Unable to fetch user details.', 'error')
            return redirect(url_for('auth.signin'))
    except Exception as e:
        flash('Error accessing user information.', 'error')
        print(f"Firebase fetch error: {e}")
        return redirect(url_for('auth.signin'))


def get_time_ago(timestamp):
    now = datetime.utcnow()
    diff = now - timestamp
    seconds = diff.total_seconds()

    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)} minutes ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)} hours ago"
    else:
        days = int(seconds / 86400)
        return f"{days} days ago" if days > 1 else "1 day ago"


#<-------------------------- appointments -------------------------------->

def generate_available_times(doctor_id, appointment_date):
    doctor = Doctor.query.get(doctor_id)
    if not doctor or doctor.status != 'Active':
        print(f"Doctor {doctor_id} not active or not found.")
        return []

    # Strip whitespace and parse times
    working_hours = doctor.time.split(' - ')
    start_time = datetime.strptime(working_hours[0].strip(), "%I:%M %p")
    end_time = datetime.strptime(working_hours[1].strip(), "%I:%M %p")

    available_times = []
    while start_time < end_time:
        available_times.append(start_time.strftime("%I:%M %p"))
        start_time += timedelta(minutes=120)  # Change increment as needed

    # Debug: print all generated times before filtering
    print(f"Generated times for Doctor {doctor_id} on {appointment_date}: {available_times}")

    # Fetch booked times for the doctor on the given date
    booked_times = [appt.appointment_time.strftime("%I:%M %p") for appt in Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status == 'Scheduled'
    ).all()]

    print(f"Booked times for Doctor {doctor_id} on {appointment_date}: {booked_times}")

    # Get current date and time
    current_datetime = datetime.now()

    # Filter out booked times and past times for the current day
    available_times = [
        time for time in available_times
        if time not in booked_times and (
            appointment_date != current_datetime.date().strftime("%Y-%m-%d") or 
            datetime.strptime(f"{appointment_date} {time}", "%Y-%m-%d %I:%M %p") > current_datetime
        )
    ]
    
    print(f"Available times after filtering for Doctor {doctor_id} on {appointment_date}: {available_times}")
    return available_times


def day_of_week(day_name):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days.index(day_name)  # Returns 0 for Monday, 1 for Tuesday, etc.

@bp.route('/get-available-times', methods=['GET'])
def get_available_times():
    doctor_id = request.args.get('doctor_id')
    date_str = request.args.get('date')
    if doctor_id and date_str:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        day_index = date.weekday()  # Monday is 0 and Sunday is 6

        doctor = Doctor.query.get(doctor_id)
        if not doctor or doctor.status != 'Active':
            return jsonify([])

        # Parse the doctor's schedule days
        schedule_days = doctor.schedule.split(' to ')
        start_day = day_of_week(schedule_days[0])
        end_day = day_of_week(schedule_days[1])

        # Check if the selected day falls within the doctor's schedule
        if start_day <= day_index <= end_day or (end_day < start_day and (day_index >= start_day or day_index <= end_day)):
            available_times = generate_available_times(doctor_id, date_str)
            return jsonify(available_times)

        return jsonify([])  # Return empty if the date is not within the doctor's working days

    return jsonify([])


@bp.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if request.method == 'POST':
        # Extract form data
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        reason = request.form.get('reason')
        notes = request.form.get('notes')

        # Get the client ID from session
        client_id = session.get('user_id')

        if not client_id:
            flash('You must be logged in to schedule an appointment.')
            return redirect(url_for('auth.signin'))

        # Generate AI-enhanced notes if the reason is provided
        if reason:
            ai_prompt = (
                "Summarize the following medical consultation reason and integrate any existing notes into a personal narrative. "
                "You are the patient describing your symptoms and experiences. Keep the summary concise, within 20 words. "
                "Use first-person pronouns like 'I', 'my', and 'me'. "
                f"Reason for visit: '{reason}'. "
                f"Existing notes: '{notes if notes else 'No additional notes provided'}'."
            )
                
            # Access your API key as an environment variable.
            genai.configure(api_key=os.environ['GOOGLE_API_KEY1'])
            # Choose a model that's appropriate for your use case.
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(ai_prompt)
            enhanced_notes = response.text.strip()
        else:
            enhanced_notes = notes  # Use existing notes if no reason is provided

        # Create a new appointment instance
        new_appointment = Appointment(
            client_id=client_id,
            doctor_id=doctor_id,
            appointment_date=datetime.strptime(appointment_date, "%Y-%m-%d").date(),
            appointment_time=datetime.strptime(appointment_time, "%I:%M %p").time(),
            status='Scheduled',
            reason=reason,
            notes=enhanced_notes
        )

        # Add the new appointment to the database
        db.session.add(new_appointment)
        db.session.commit()

        flash('Appointment scheduled successfully!', 'success')
        return redirect(url_for('patient.appointments'))

    # Only fetch appointments for the logged-in user
    client_id = session.get('user_id')

    if not client_id:
        flash('You must be logged in to view your appointments.')
        return redirect(url_for('auth.signin'))

    # Filter appointments for the specific client ID
    now = datetime.now()
    upcoming_appointments = Appointment.query.filter(
        Appointment.client_id == client_id,  # Filter for the logged-in user's appointments
        (Appointment.appointment_date > now.date()) | 
        ((Appointment.appointment_date == now.date()) & (Appointment.appointment_time >= now.time())),
        Appointment.status != 'Cancelled'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

    # Fetch active doctors
    doctors = Doctor.query.filter_by(status='Active').all()

    # Generate timeslots for each doctor
    doctor_timeslots = {doctor.doctor_id: generate_available_times(doctor.doctor_id, now.date()) for doctor in doctors}
    
    today_date = now.strftime("%Y-%m-%d")
    
    return render_template(
        'clients/appointments.html',
        upcoming_appointments=upcoming_appointments,
        doctors=doctors,
        doctor_timeslots=doctor_timeslots,
        today_date=today_date
    )


@bp.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if appointment:
        db.session.delete(appointment)  # This deletes the appointment from the database
        db.session.commit()
        flash('Appointment cancelled and removed successfully.')
    else:
        flash('Appointment not found.')
    return redirect(url_for('patient.appointments'))


#<-------------------------- messages -------------------------------->

@bp.route('/messages', methods=['GET'])
def messages():
    if 'user' not in session or session.get('user_type') not in ['patient', 'client']:
        return redirect(url_for('auth.signin'))

    client_id = session.get('user_id')
    all_doctors = Doctor.query.filter_by(status='Active').all()  # Only get active doctors

    # Retrieve messages based on client_id and doctor_id from the Account table
    messages_sent = Message.query.filter_by(sender_id=client_id).all()
    messages_received = Message.query.filter_by(recipient_id=client_id).all()

    # Collect unique doctor IDs from messages
    account_ids = set([msg.recipient_id for msg in messages_sent] + [msg.sender_id for msg in messages_received])
    unique_doctors = {}

    for account_id in account_ids:
        account = Account.query.filter_by(id=account_id).first()
        if account:
            doctor = Doctor.query.filter_by(doctor_id=account.doctor_id).first()
            if doctor:
                # Get the last message for this conversation
                last_message = Message.query.filter(
                    or_(
                        and_(Message.sender_id == client_id, Message.recipient_id == account.id),
                        and_(Message.sender_id == account.id, Message.recipient_id == client_id)
                    )
                ).order_by(Message.timestamp.desc()).first()

                if last_message:
                    unique_doctors[doctor.doctor_id] = {
                        'doctor_name': f"{doctor.first_name} {doctor.last_name}",
                        'last_message': last_message.body,
                        'timestamp': last_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    }

    # Mark all message notifications as read for this client
    unread_notifications = Notification.query.filter_by(patient_id=client_id, is_read=False, notification_type='message').all()
    for notification in unread_notifications:
        notification.is_read = True
        
    unread_messages = Message.query.filter_by(recipient_id=client_id, is_read=False).all()
    for message in unread_messages:
        message.is_read = True
        
    db.session.commit()
    
    unique_doctors_list = [{'doctor_id': k, **v} for k, v in unique_doctors.items()]
    return render_template('clients/messages.html', all_doctors=all_doctors, unique_doctors=unique_doctors_list)

@bp.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        sender_id = session.get('user_id')
        doctor_id = data.get('doctor_id')
        body = data.get('message')
        timestamp = datetime.utcnow()

        account = Account.query.filter_by(doctor_id=doctor_id).first()
        if not account:
            return jsonify({'success': False, 'error': 'Doctor account not found'}), 404

        receiver_id = account.id

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
            doctor_id=account.doctor_id, 
            patient_id=receiver_id,
            message=f"New message from your doctor: {body}",
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
    doctor_id = request.args.get('doctor_id')

    # Retrieve the doctor's account ID using doctor_id
    account = Account.query.filter_by(doctor_id=doctor_id).first()
    if not account:
        return jsonify({'success': False, 'error': 'Doctor account not found'}), 404

    receiver_id = account.id

    if not sender_id or not receiver_id:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    # Fetch messages from the database using receiver_id
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == sender_id, Message.recipient_id == receiver_id),
            and_(Message.sender_id == receiver_id, Message.recipient_id == sender_id)
        )
    ).order_by(Message.timestamp.asc()).all()

    # Create a list of messages with necessary details
    conversation = [{
        'sender': 'You' if msg.sender_id == sender_id else 'Doctor',
        'message': msg.body,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in messages]

    return jsonify({'success': True, 'conversation': conversation}), 200

#<-------------------------- AI Chatbot -------------------------------->
# Fetch user data function
def fetch_user_data(user_id):
    user_data = User.query.get(user_id)
    if user_data:
        client_account = ClientAccounts.query.filter_by(client_id=user_data.user_id).first()
        if client_account:
            return {
                'first_name': client_account.first_name,
                'last_name': client_account.last_name,
                'email': client_account.email,
                'phone_number': client_account.phone_number,
                'address': client_account.address
            }
    return None

def fetch_user_appointment(user_id):
    appointments = Appointment.query.filter_by(client_id=user_id).all()
    if appointments:
        return [
            {
                'doctor': f"Dr. {appt.doctor.first_name} {appt.doctor.last_name}",
                'date': appt.appointment_date.strftime('%Y-%m-%d'),
                'time': appt.appointment_time.strftime('%I:%M %p'),
                'reason': appt.reason if appt.reason else 'No reason provided',
                'notes': appt.notes if appt.notes else 'No additional notes'

            }
            for appt in appointments
        ]
    return None

def fetch_user_medication(user_id):
    medications = Medication.query.filter_by(client_id=user_id).all()
    if medications:
        return [
            {
                'medication_name': med.medication_name,
                'dosage': med.dosage,
                'frequency': med.frequency,
                'start_date': med.start_date.strftime('%Y-%m-%d'),
                'end_date': med.end_date.strftime('%Y-%m-%d'),
                'notes': med.notes if med.notes else 'No additional notes'
            }
            for med in medications
        ]
    return None

def fetch_user_lab_results(user_id):
    lab_results = LabResult.query.filter_by(patient_id=user_id).all()
    if lab_results:
        return [
            {
                'test_name': result.lab_test.test_name,
                'result_value': result.result_value,
                'unit': result.unit,
                'reference_range': result.reference_range,
                'date': result.result_date.strftime('%Y-%m-%d'),
                'notes': result.notes if result.notes else 'No additional notes'
            }
            for result in lab_results
        ]
    return None

def fetch_user_doctors(user_id):
    Doctors = Doctor.query.filter_by(doctor_id=user_id).all()
    if Doctors:
        return [
            {
                'doctor_name': doctor.doctor_name,
                'specialization': doctor.specialization,
                'schedule': doctor.schedule,
                'time': doctor.time
            }
            for doctor in Doctors
        ]
    
    return None

@bp.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User not logged in'}), 401

    client_account = ClientAccounts.query.get(user_id)
    if not client_account:
        return jsonify({'success': False, 'error': 'Client account not found'}), 404
    
    appointment_details = fetch_user_appointment(user_id)
    if appointment_details:
        appointment_info = [
            f"Appointment with {appt['doctor']} on {appt['date']} at {appt['time']} for {appt['reason']}"
            for appt in appointment_details
        ]
        print(appointment_info)
    else:
        appointment_info = "No upcoming appointments found."

    

    medication_details = fetch_user_medication(user_id)
    if medication_details:
        medication_info = [
            f"{med['medication_name']} - Dosage: {med['dosage']}, Frequency: {med['frequency']}, Notes: {med['notes']}"
            for med in medication_details
        ]
        print(medication_info)
    else:
        medication_info = "No active medications found."

    lab_results = fetch_user_lab_results(user_id)
    if lab_results:
        lab_results_info = [
            f"{result['test_name']} - Result: {result['result_value']} {result['unit']} (Reference Range: {result['reference_range']}), Date: {result['date']}, Notes: {result['notes']}"
            for result in lab_results
        ]
        print(lab_results_info)
    else:
        lab_results_info = "No lab results found."

    doctors = fetch_user_doctors(user_id)
    if doctors:
        doctor_info = [
            f"{doctor['doctor_name']} - Specialization: {doctor['specialization']}, Schedule: {doctor['schedule']}"
            for doctor in doctors
        ]
        print(doctor_info)
    else:
        doctor_info = "No doctor appointments found."

    # List of greeting messages
    greetings = [
        "Hi <strong>{first_name}</strong>! 😊 I'm Lumix, your dedicated Health Assistant at LuminaMedix. How can I help you today?",
        "Welcome <strong>{first_name}</strong>! 👋 This is Lumix from LuminaMedix. What can I assist you with today?",
        "Good day, <strong>{first_name}</strong>! 🌞 I'm Lumix, your AI Health Companion. How may I support your health needs today?",
        "Hello <strong>{first_name}</strong>! 🌟 Lumix here, your personal health guide from LuminaMedix. What assistance do you need?",
        "Greetings <strong>{first_name}</strong>! 🙌 I am Lumix, your AI Health Assistant at LuminaMedix. How may I be of service today?",
        "Hi there, <strong>{first_name}</strong>! 🤗 I'm Lumix from LuminaMedix. What health queries do you have today?",
        "Hello <strong>{first_name}</strong>! 💪 Lumix at your service from LuminaMedix. How can I make your day healthier?",
        "Welcome back, <strong>{first_name}</strong>! 🔄 Lumix here to help you with your healthcare needs. What's on your mind today?",
        "Hi <strong>{first_name}</strong>! 📞 It's Lumix, your trusted Health Assistant from LuminaMedix. What can I help you with today?",
        "Good to see you, <strong>{first_name}</strong>! 😃 I'm Lumix, ready to assist you with your health concerns. How may I help?",
        "Hello <strong>{first_name}</strong>! 🔍 Lumix here, your Health Assistant at LuminaMedix. Need assistance with anything specific today?",
        "Hey <strong>{first_name}</strong>! 👀 I'm Lumix from LuminaMedix. Let me know how I can assist you with your health today.",
        "Hi <strong>{first_name}</strong>, Lumix speaking. 🎤 Welcome to LuminaMedix. What can I do for you today?",
        "Hello <strong>{first_name}</strong>! 🏥 I'm Lumix, your AI companion from LuminaMedix. How can I assist you in achieving better health today?",
        "Greetings <strong>{first_name}</strong>! 🌿 Lumix at LuminaMedix here. How can I support your wellness journey today?",
        "Hi <strong>{first_name}</strong>! 🌼 Lumix from LuminaMedix here. What can I do to help you feel your best today?",
        "Hello <strong>{first_name}</strong>! 🌸 I'm Lumix, your friendly Health Assistant. How can I assist you with your health today?",
        "Good morning, <strong>{first_name}</strong>! ☀️ Lumix here to help you start your day on a healthy note. What can I assist you with?",
        "Hi <strong>{first_name}</strong>! 🌺 This is Lumix from LuminaMedix. How can I help you achieve your health goals today?",
        "Welcome <strong>{first_name}</strong>! 🌼 Lumix here, your personal health assistant. How can I support your health journey today?",
        "Hello <strong>{first_name}</strong>! 🌞 I'm Lumix, your AI Health Assistant. What health concerns can I help you with today?",
        "Hi <strong>{first_name}</strong>! 🌟 Lumix from LuminaMedix here. How can I make your day healthier and happier?",
        "Good afternoon, <strong>{first_name}</strong>! 🌅 Lumix here to assist you with any health questions. How can I help?",
        "Hi <strong>{first_name}</strong>! 🌻 I'm Lumix, your dedicated health companion. What can I do for you today?",
        "Hello <strong>{first_name}</strong>! 🌷 Lumix here from LuminaMedix. How can I support your health and wellness today?",
        "Greetings <strong>{first_name}</strong>! 🌟 I'm Lumix, your AI Health Assistant. How may I assist you in achieving better health today?",
        "Hi <strong>{first_name}</strong>! 🌼 Lumix here to help you with your health needs. What can I do for you today?",
        "Good evening, <strong>{first_name}</strong>! 🌙 Lumix from LuminaMedix here. How can I assist you with your health tonight?",
        "Hello <strong>{first_name}</strong>! 🌺 I'm Lumix, your friendly health guide. How can I support your health journey today?",
        "Hi <strong>{first_name}</strong>! 🌸 Lumix here to assist you with any health concerns. What can I help you with today?",
        "Welcome <strong>{first_name}</strong>! 🌿 Lumix from LuminaMedix at your service. How can I support your health today?",
        "Good to see you, <strong>{first_name}</strong>! 🌞 I'm Lumix, your dedicated health assistant. How can I help you today?",
        "Hello <strong>{first_name}</strong>! 🌟 Lumix here to assist you with your health needs. What can I do for you today?",
        "Hi <strong>{first_name}</strong>! 🌼 This is Lumix from LuminaMedix. How can I support your health and wellness today?",
        "Greetings <strong>{first_name}</strong>! 🌸 Lumix here to help you with any health questions. How can I assist you today?",
        "Welcome back, <strong>{first_name}</strong>! 🌿 Lumix here to support your health journey. What can I help you with today?",
        "Hi <strong>{first_name}</strong>! 🌞 I'm Lumix, your AI Health Assistant. How can I assist you with your health today?",
        "Hello <strong>{first_name}</strong>! 🌟 Lumix from LuminaMedix here. How can I support your health and wellness today?",
        "Good day, <strong>{first_name}</strong>! 🌻 Lumix here to help you with your health needs. What can I do for you today?",
        "Hi <strong>{first_name}</strong>! 🌺 This is Lumix from LuminaMedix. How can I assist you with your health today?",
        "Hello <strong>{first_name}</strong>! 🌷 Lumix here to support your health journey. What can I help you with today?",
        "Greetings <strong>{first_name}</strong>! 🌟 I'm Lumix, your AI Health Assistant. How can I assist you in achieving better health today?"
    ]


    # Select a random greeting message
    greeting_message = random.choice(greetings).format(first_name=client_account.first_name)

    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message')
        message = data.get('message')
        language = data.get('language', 'en')
        topic = data.get('topic')
        if topic:
            message = f"Tell me about {topic}"

        if message:
            user_context = (
                f"User information: Name: {client_account.first_name} {client_account.last_name}, "
                f"Email: {client_account.email}, Phone: {client_account.phone_number}"
            )
            advanced_instruction = (
                "Your task is to assist patients with general health information and management. "
                "You should provide detailed information about symptoms, potential causes, and possible treatments for common ailments. "
                "Additionally, offer advice on preventive measures, lifestyle changes, and when to seek professional medical advice. "
                "Ensure to use patient-friendly language and make the information as concise as possible. "
                "Highlight any important terms or actions in **bold** for better readability. "
                "Maintain a supportive and empathetic tone throughout your responses. "
                "Here are some specific guidelines to follow: "

                "1. **Symptom Lists**: When listing symptoms, provide a clear and concise list of symptoms associated with the condition. "
                "   Example: <ul><li>Headache</li><li>Fever</li><li>Cough</li></ul> "

                "2. **Treatment Options**: Discuss potential treatment options in a prioritized manner, indicating the most common or effective treatments first. "
                "   Example: <ol><li>Rest and hydration</li><li>Over-the-counter medications</li><li>Consult a doctor if symptoms persist</li></ol> "

                "3. **Preventive Measures**: Offer actionable preventive measures to help patients avoid common health issues. "
                "   Example: <ul><li>Wash hands regularly</li><li>Maintain a balanced diet</li><li>Exercise regularly</li></ul> "

                "4. **Professional Advice**: Always recommend seeking professional medical advice if symptoms persist or worsen. "
                "   Example: <p>If symptoms persist for more than a week, please consult a healthcare professional.</p> "

                "5. **Lab Results Interpretation**: Provide clear explanations of lab results, including what the results mean and the normal ranges. "
                "   Example: <table><tr><th>Test</th><th>Result</th><th>Normal Range</th></tr><tr><td>Sodium</td><td>139 mEq/L</td><td>135-145 mEq/L</td></tr></table> "

                "6. **Appointment Management**: Give clear instructions for managing appointments, including how to reschedule, edit, and cancel appointments. "
                "   Example: <p>To reschedule your appointment, click the 'Reschedule' button next to the appointment details.</p> "

                "7. **Doctor Information**: Present information about doctors, including their specialization, status, and schedule. "
                "   Example: <table><tr><th>Doctor</th><th>Specialization</th><th>Status</th><th>Schedule</th></tr><tr><td>Dr. John Doe</td><td>Cardiology</td><td>Active</td><td>Mon-Fri, 9am-5pm</td></tr></table> "

                "8. **Health Tips**: Provide general health tips and lifestyle advice to promote overall well-being. "
                "   Example: <ul><li>Stay hydrated</li><li>Get at least 7-8 hours of sleep</li><li>Avoid smoking and excessive alcohol consumption</li></ul> "

                "9. **Emergency Situations**: Clearly outline steps to take in emergency situations, emphasizing the importance of seeking immediate medical attention. "
                "   Example: <p>If you experience severe chest pain, difficulty breathing, or sudden loss of consciousness, call emergency services immediately.</p> "

                "10. **Medication Information**: Provide detailed information about common medications, including usage, dosage, and potential side effects. "
                "    Example: <p>Paracetamol: Used to relieve pain and reduce fever. Dosage: 500mg every 4-6 hours as needed. Do not exceed 4g per day.</p> "

                "11. **Health Monitoring**: Encourage patients to monitor their health metrics regularly and provide guidance on how to do so. "
                "    Example: <p>Keep track of your blood pressure, blood sugar levels, and weight regularly to manage your health effectively.</p> "

                "12. **Mental Health Support**: Offer support and resources for mental health, emphasizing the importance of seeking help when needed. "
                "    Example: <p>If you are feeling overwhelmed or anxious, consider speaking to a mental health professional. There are also many online resources and support groups available.</p> "

                "13. **Query Limitations**: You are only permitted to answer health-related questions or queries about personal information such as names and appointments. "
                "    If a user asks about unrelated subjects, inform them that you cannot provide information on that topic. "
                "    Example: <p>I'm sorry, but I can only assist with health-related questions and information about your appointments. Please contact the appropriate service for other inquiries.</p> "
            )

            formatting_instruction = (
                "Use HTML tags to format the response appropriately and enhance readability. "
                "Here are some specific guidelines to follow: "

                "1. **Bold Text**: Use the <strong> tag to make important terms or actions bold. "
                "   Example: <strong>important term</strong> "

                "2. **Line Breaks**: Use the <br> tag to create line breaks where necessary. "
                "   Example: <p>Line one.<br>Line two.</p> "

                "3. **Unordered Lists**: Use the <ul> and <li> tags to create unordered lists for symptoms, preventive measures, and health tips. "
                "   Example: <ul><li>Symptom 1</li><li>Symptom 2</li></ul> "

                "4. **Ordered Lists**: Use the <ol> and <li> tags to create ordered lists for treatment options or steps to follow. "
                "   Example: <ol><li>Step 1</li><li>Step 2</li></ol> "

                "5. **Paragraphs**: Use the <p> tag to create paragraphs for general information and advice. "
                "   Example: <p>This is a paragraph.</p> "

                "6. **Tables**: Use the <table>, <tr>, <th>, and <td> tags to present tabular data clearly. "
                "   Example: <table><tr><th>Test</th><th>Result</th><th>Normal Range</th></tr><tr><td>Sodium</td><td>139 mEq/L</td><td>135-145 mEq/L</td></tr></table> "

                "7. **Color Coding**: Use inline CSS to apply color coding to differentiate between different types of information. "
                "   Example: <p style='color: green;'>Positive action.</p> <p style='color: red;'>Warning or important note.</p> "

                "8. **Visual Aids**: Include visual aids such as images or icons to enhance understanding. "
                "   Example: <p><img src='hydration.png' alt='Stay Hydrated' width='100' height='100'> Stay hydrated by drinking at least 8 glasses of water a day.</p> "

                "9. **Interactive Elements**: Suggest interactive elements like quizzes or self-assessment tools to engage users. "
                "   Example: <p>Take our <a href='self-assessment.html'>self-assessment quiz</a> to understand your symptoms better.</p> "

                "10. **Consistent Font Size**: Ensure all text is of consistent font size, except for titles and headings. "
                "    Example: Use <h1>, <h2>, etc., for headings and <p> for regular text. "

                "11. **Titles and Headings**: Use <h1>, <h2>, <h3>, etc., to create a hierarchy of titles and headings. "
                "    Example: <h1>Main Title</h1> <h2>Subheading</h2> "

                "12. **Spacing and Alignment**: Ensure adequate spacing between elements for a clean and organized layout. "
                "    Example: Use margin and padding CSS properties to adjust spacing. "

                "By following these formatting guidelines, you will be able to create visually appealing and easy-to-read responses that enhance the user experience."
                )

            prompt = f"{user_context}\n\n{advanced_instruction}\n\n{formatting_instruction}\n\nUser: {message}\nLanguage: {language}\n Appointment Information: {appointment_info} \n Medication Information: {medication_info} \n Lab Results: {lab_results_info} \n Doctor Information: {doctor_info}"

            try:
                genai.configure(api_key=os.environ['GOOGLE_API_KEY1'])
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                bot_reply = response.text.strip()

                # Add logic to check for specific queries like appointments
                if 'appointment' in message.lower():
                    appointments = Appointment.query.filter_by(client_id=client_account.client_id).all()
                    if appointments:
                        appointment_details = [
                            f"Appointment with Dr. {appt.doctor.first_name} {appt.doctor.last_name} on {appt.appointment_date.strftime('%Y-%m-%d')} at {appt.appointment_time.strftime('%I:%M %p')}"
                            for appt in appointments
                        ]
                        appointment_reply = "You have the following appointments:\n" + "\n".join(appointment_details)
                    else:
                        appointment_reply = "You do not have any scheduled appointments."
                    bot_reply = f"<strong>Appointment Information:</strong>\n{appointment_reply}"

                # Format the AI's response
                bot_reply = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', bot_reply)
                bot_reply = re.sub(r'(\d+)\.\s', r'<br>\1. ', bot_reply)  # New line for each numbered point
                bot_reply = re.sub(r'•\s', r'<br>• ', bot_reply)  # New line for each bullet point
                bot_reply = re.sub(r'(\b[A-Z][a-z]*:)', r'<br><strong>\1</strong>', bot_reply)  # Bold headings
                bot_reply = re.sub(r'\* (.*?)\n', r'<br>• \1<br>', bot_reply)  # New line for each single star list item

                return jsonify({'success': True, 'bot_reply': bot_reply}), 200
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        return jsonify({'success': False, 'error': 'Missing message'}), 400

    return render_template('clients/chatbot.html', first_name=client_account.first_name, greeting_message=greeting_message)


#<-------------------------- profile -------------------------------->
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.signin'))
    
    client_account = ClientAccounts.query.get(user_id)
    
    # Fetch or create patient info if not exists
    patient_info = Patient.query.get(user_id)
    if not patient_info:
        # Create a new Patient record if it doesn't exist
        patient_info = Patient(patient_id=user_id)
        db.session.add(patient_info)
        db.session.commit()

    if request.method == 'POST':
        form_name = request.form.get('form_name')
        
        if form_name == 'personal_info':
            # Update personal info
            client_account.first_name = request.form.get('first_name')
            client_account.last_name = request.form.get('last_name')
            if patient_info:
                # Convert the date string to a date object
                dob_str = request.form.get('dob')
                if dob_str:
                    patient_info.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()  # Convert string to date
                else:
                    patient_info.dob = None

                patient_info.gender = request.form.get('gender') or None

            # Handle profile picture upload
            if 'profile_picture' in request.files:
                profile_picture = request.files['profile_picture']
                if profile_picture and allowed_file(profile_picture.filename):
                    filename = secure_filename(profile_picture.filename)
                    image_path = os.path.join(UPLOAD_FOLDER, filename)
                    profile_picture.save(image_path)

                    # Update path to use forward slashes and make it relative to 'static'
                    patient_info.image_path = os.path.relpath(image_path, start='app/static').replace("\\", "/")

            db.session.commit()
            flash('Personal information updated successfully', 'success')
        
        elif form_name == 'contact_details':
            # Update contact details
            client_account.email = request.form.get('email')
            client_account.phone_number = request.form.get('phone')
            client_account.address = request.form.get('address')
            db.session.commit()
            flash('Contact details updated successfully', 'success')
        
        elif form_name == 'preferences':
            # Update preferences
            client_account.language = request.form.get('language')
            client_account.timezone = request.form.get('timezone')
            client_account.email_notifications = 'email_notifications' in request.form
            client_account.sms_notifications = 'sms_notifications' in request.form
            db.session.commit()
            flash('Preferences updated successfully', 'success')
        
        elif form_name == 'security_settings':
            # Implement password change logic here
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            user = User.query.get(user_id)

            if not user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match', 'danger')
            else:
                user.set_password(new_password)
                db.session.commit()
                flash('Password updated successfully!', 'success')

    return render_template('clients/profile.html', client_account=client_account, patient_info=patient_info)

# Update personal info
@bp.route('/profile/update_personal_info', methods=['POST'])
def update_personal_info():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')
    client_account = ClientAccounts.query.get(user_id)
    patient_info = Patient.query.get(user_id)

    if not patient_info:
        # Create a new Patient record if it doesn't exist
        patient_info = Patient(patient_id=user_id)
        db.session.add(patient_info)

    client_account.first_name = request.form['first_name']
    client_account.last_name = request.form['last_name']
    
    # Convert the date string to a date object
    dob_str = request.form.get('dob')
    if dob_str:
        patient_info.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()  # Convert string to date
    else:
        patient_info.dob = None

    patient_info.gender = request.form['gender'] or None

    # Handle profile picture upload
    if 'profile_picture' in request.files:
        profile_picture = request.files['profile_picture']
        if profile_picture and allowed_file(profile_picture.filename):
            filename = secure_filename(profile_picture.filename)
            profile_picture.save(os.path.join(UPLOAD_FOLDER, filename))
            client_account.profile_picture = os.path.join(UPLOAD_FOLDER, filename)

    db.session.commit()
    flash('Personal information updated successfully!', 'success')
    return redirect(url_for('patient.profile'))

# Update contact details
@bp.route('/profile/update_contact_details', methods=['POST'])
def update_contact_details():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')
    client_account = ClientAccounts.query.get(user_id)

    client_account.email = request.form['email']
    client_account.phone_number = request.form['phone']
    client_account.address = request.form['address']
    db.session.commit()
    flash('Contact details updated successfully!', 'success')
    return redirect(url_for('patient.profile'))

# Update preferences
@bp.route('/profile/update_preferences', methods=['POST'])
def update_preferences():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')
    client_account = ClientAccounts.query.get(user_id)

    client_account.language = request.form['language']
    client_account.timezone = request.form['timezone']
    client_account.email_notifications = 'email_notifications' in request.form
    client_account.sms_notifications = 'sms_notifications' in request.form
    db.session.commit()
    flash('Preferences updated successfully!', 'success')
    return redirect(url_for('patient.profile'))

# Update security settings
@bp.route('/profile/update_security_settings', methods=['POST'])
def update_security_settings():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if not user.check_password(current_password):
        flash('Current password is incorrect', 'danger')
    elif new_password != confirm_password:
        flash('New passwords do not match', 'danger')
    else:
        user.set_password(new_password)
        db.session.commit()
        flash('Password updated successfully!', 'success')

    return redirect(url_for('patient.profile'))

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
    # Ensure the user is logged in and is a patient
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    # Get the logged-in patient's ID
    patient_id = session.get('user_id')

    # Query to fetch the lab results for the logged-in patient
    test_results = db.session.query(LabResult, LabTest).join(LabTest, LabResult.test_id == LabTest.test_id)\
        .filter(LabResult.patient_id == patient_id).order_by(LabResult.result_date.desc()).all()

    return render_template('clients/test_results.html', test_results=test_results)

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

@bp.route('/schedule_now')
def schedule_now():
    # Logic to schedule a blood test
    return redirect(url_for('dashboard'))

@bp.route('/find_specialist')
def find_specialist():
    # Logic to find a specialist
    return redirect(url_for('dashboard'))

#<-------------------------- visits -------------------------------->
@bp.route('/visits')
def visits():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')

    # Fetch visit history
    visits = Visit.query.all()

    print(visits)

    # Fetch the latest visit
    latest_visit = visits[0] if visits else None

    # Extract additional details if latest visit is available
    latest_visit_details = None
    if latest_visit:
        latest_visit_details = {
            "symptoms": ["Fatigue", "Joint pain", "Occasional headaches"],  # Replace with actual data if available
            "medications": [
                {"name": "Vitamin D", "action": "New prescription", "action_color": "green"},
                {"name": "Ibuprofen", "action": "Dosage increased", "action_color": "yellow"},
                {"name": "Allergy medication", "action": "Discontinued", "action_color": "red"}
            ],
            "notes": "Patient shows improvement in overall health markers. Recommended lifestyle changes appear to be effective. Continue monitoring and adjust treatment plan as needed."
        }

    # Fetch follow-up actions
    follow_up_actions = FollowUpAction.query.all()

    return render_template('clients/visits.html', visits=visits, latest_visit=latest_visit_details, follow_up_actions=follow_up_actions)

# @bp.route('/visits')
# def visits():
#     if 'user' not in session or session.get('user_type') != 'patient':
#         return redirect(url_for('auth.signin'))
    
#     # Fetch visit history, latest visit details, and follow-up actions from the database
#     visits = [
#         {"date": datetime(2024, 7, 15), "doctor_name": "Dr. John Smith", "summary": "Routine check-up, recommended vitamin D supplementation.", "next_steps": "Follow-up in 3 months."},
#         {"date": datetime(2024, 10, 20), "doctor_name": "Dr. Jane Doe", "summary": "Follow-up visit, improved health markers.", "next_steps": "Annual check-up scheduled for next year."},
#         {"date": datetime(2025, 1, 10), "doctor_name": "Dr. John Smith", "summary": "Discussing long-term treatment options for chronic conditions.", "next_steps": "Review new medications in 6 months."}
#     ]
    
#     latest_visit = {
#         "symptoms": ["Fatigue", "Joint pain", "Occasional headaches"],
#         "medications": [
#             {"name": "Vitamin D", "action": "New prescription", "action_color": "green"},
#             {"name": "Ibuprofen", "action": "Dosage increased", "action_color": "yellow"},
#             {"name": "Allergy medication", "action": "Discontinued", "action_color": "red"}
#         ],
#         "notes": "Patient shows improvement in overall health markers. Recommended lifestyle changes appear to be effective. Continue monitoring and adjust treatment plan as needed."
#     }
    
#     follow_up_actions = [
#         {"title": "Blood Test", "description": "Schedule a follow-up blood test in 2 weeks", "action_text": "Schedule Now"},
#         {"title": "Specialist Referral", "description": "Book an appointment with a rheumatologist", "action_text": "Find Specialist"},
#         {"title": "Medication Review", "description": "Review effectiveness of new prescriptions in 1 month", "action_text": "Set Reminder"}
#     ]
    
#     return render_template('clients/visits.html', visits=visits, latest_visit=latest_visit_details, follow_up_actions=follow_up_actions)

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

#     return render_template('profile_settings.html', patient=patient)'
