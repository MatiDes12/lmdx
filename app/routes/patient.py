
from mailbox import Message
import os
from flask import Blueprint, json, jsonify, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Appointment, Medication, Reminder, User, Message
from flask import Blueprint, jsonify, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Appointment, Medication, Reminder, User, Message, Patient
from .. import sqlalchemy_db as db
from datetime import datetime, timedelta
from app.routes.auth import firebase_db
import google.generativeai as genai
from dotenv import load_dotenv

from sqlalchemy import and_, or_

bp = Blueprint('patient', __name__)

# Load environment variables from .env file
load_dotenv()



#<-------------------------- dashboard -------------------------------->

@bp.route('/dashboard')
def patient_dashboard():
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
    available_times = [time for time in available_times if time not in booked_times and (appointment_date != current_datetime.date().strftime("%Y-%m-%d") or datetime.strptime(f"{appointment_date} {time}", "%Y-%m-%d %I:%M %p") > current_datetime)]
    
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


#<-------------------------- appointments -------------------------------->
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

        new_appointment = Appointment(
            client_id=client_id,
            doctor_id=doctor_id,
            appointment_date=datetime.strptime(appointment_date, "%Y-%m-%d").date(),
            appointment_time=datetime.strptime(appointment_time, "%I:%M %p").time(),
            status='Scheduled',
            reason=reason,
            notes=enhanced_notes
        )
        db.session.add(new_appointment)
        db.session.commit()
        return redirect(url_for('patient.appointments'))

    doctors = Doctor.query.all()
    now = datetime.now()
    upcoming_appointments = Appointment.query.filter(
        (Appointment.appointment_date > now.date()) | 
        ((Appointment.appointment_date == now.date()) & (Appointment.appointment_time >= now.time())),
        Appointment.status != 'Cancelled'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    doctor_timeslots = {doctor.doctor_id: generate_available_times(doctor.doctor_id, now.date()) for doctor in doctors}
    today_date = now.strftime("%Y-%m-%d")
    
    return render_template('clients/appointments.html', 
                           upcoming_appointments=upcoming_appointments,
                           doctors=doctors,
                           doctor_timeslots=doctor_timeslots,
                           today_date=today_date)


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
    all_doctors = Doctor.query.all()
    messages_sent = Message.query.filter_by(sender_id=client_id).all()
    messages_received = Message.query.filter_by(recipient_id=client_id).all()
    
    doctor_ids = set([msg.recipient_id for msg in messages_sent] + [msg.sender_id for msg in messages_received])
    print("doctor_ids: ",doctor_ids)
    unique_doctors = {}
    
    for doctor_id in doctor_ids:
        doctor = Doctor.query.filter_by(doctor_id=doctor_id).first()
        if doctor:
            last_message = Message.query.filter(
                or_(
                    and_(Message.sender_id == client_id, Message.recipient_id == doctor_id),
                    and_(Message.sender_id == doctor_id, Message.recipient_id == client_id)
                )
            ).order_by(Message.timestamp.desc()).first()
            
            if last_message:
                unique_doctors[doctor.doctor_id] = {
                    'doctor_name': f"{doctor.first_name} {doctor.last_name}",
                    'last_message': last_message.body,
                    'timestamp': last_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                
    unique_doctors_list = [{'doctor_id': k, **v} for k, v in unique_doctors.items()]
    return render_template('clients/messages.html', all_doctors=all_doctors, unique_doctors=unique_doctors_list)


@bp.route('/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        sender_id = session.get('user_id')
        receiver_id = data.get('doctor_id')
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

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/get_messages', methods=['GET'])
def get_messages():
    sender_id = session.get('user_id')
    receiver_id = request.args.get('doctor_id')

    if not sender_id or not receiver_id:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    messages = Message.query.filter(
        (Message.sender_id == sender_id) & (Message.recipient_id == receiver_id) |
        (Message.sender_id == receiver_id) & (Message.recipient_id == sender_id)
    ).order_by(Message.timestamp.asc()).all()

    conversation = [{
        'sender': 'You' if msg.sender_id == sender_id else 'Doctor',
        'message': msg.body,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in messages]

    return jsonify({'success': True, 'conversation': conversation}), 200

#<-------------------------- profile -------------------------------->

@bp.route('/profile')
def profile():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    return render_template('clients/profile.html', user=user)


@bp.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    user.first_name = request.form.get('first_name')
    user.last_name = request.form.get('last_name')
    user.email = request.form.get('email')
    user.phone = request.form.get('phone')
    user.address = request.form.get('address')
    user.city = request.form.get('city')
    user.state = request.form.get('state')
    user.zipcode = request.form.get('zipcode')
    
    db.session.commit()
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



