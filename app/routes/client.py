from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Patient, Appointment, Message, LabResult, Medication
from .. import sqlalchemy_db as db
from datetime import datetime
from app.routes.auth import firebase_db

bp = Blueprint('client', __name__)


from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Patient, Appointment
from .. import sqlalchemy_db as db
from datetime import datetime
from app.routes.auth import firebase_db

bp = Blueprint('client', __name__)

@bp.route('/dashboard')
def dashboard():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    id_token = session.get('user_id_token')  # Also ensure that the Firebase ID token is stored in session
    
    try:
        # Fetch user data from Firebase
        user_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
        if user_data:
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

@bp.route('/appointments', methods=['GET'])
def appointments():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    
    doctors = Doctor.query.all()
    return render_template('clients/appointments.html', doctors=doctors)

@bp.route('/make_appointment', methods=['POST'])
def make_appointment():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    doctor_id = request.form.get('doctor_id')
    date = request.form.get('date')
    time = request.form.get('time')
    notes = request.form.get('notes', '')
    
    if not all([doctor_id, date, time]):
        flash('All fields are required.', 'error')
        return redirect(url_for('client.appointments'))

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
    
    return redirect(url_for('client.dashboard'))




@bp.route('/messages', methods=['GET'])
def messages():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))

    doctors = Doctor.query.all()
    return render_template('clients/messages.html', doctors=doctors)


@bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))

    doctor_id = request.form.get('doctor_id')
    content = request.form.get('content')
    patient_id = session.get('user_id')  # Assuming the client is a patient and their ID is stored in the session

    if not doctor_id or not content:
        flash('All fields are required.', 'danger')
        return redirect(url_for('client.messages'))

    message = Message(
        patient_id=patient_id,
        doctor_id=doctor_id,
        content=content,
        status='sent',
        timestamp=datetime.utcnow()
    )

    db.session.add(message)
    db.session.commit()

    flash('Message sent successfully!', 'success')
    return redirect(url_for('client.messages'))



@bp.route('/test_results')
def test_results():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    return render_template('clients/test_results.html')

@bp.route('/medication')
def medication():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    return render_template('clients/medication.html')

@bp.route('/visits')
def visits():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    return render_template('clients/visits.html')


@bp.route('/billing')
def billing():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    return render_template('clients/billing.html')

@bp.route('/insurance')
def insurance():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    return render_template('clients/insurance.html')
