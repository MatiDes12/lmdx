from mailbox import Message
from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from datetime import datetime
from ..models_db import Doctor, Appointment
from .. import sqlalchemy_db as db
from app.routes.auth import firebase_db

bp = Blueprint('client', __name__)

@bp.route('/dashboard')
def dashboard():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))

    user_id = session.get('user_id')
    id_token = session.get('user_id_token')

    try:
        # Fetch user data from Firebase
        user_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
        if user_data:
            # Fetch scheduled appointments for the logged-in user
            appointments = Appointment.query.filter_by(patient_id=user_id, status='Scheduled').order_by(Appointment.date.asc(), Appointment.time.asc()).all()
            return render_template('clients/dashboard.html', first_name=user_data.get('first_name'), last_name=user_data.get('last_name'), appointments=appointments)
        else:
            flash('Unable to fetch user details.', 'error')
            return redirect(url_for('auth.signin'))
    except Exception as e:
        flash('Error accessing user information.', 'error')
        print(f"Firebase fetch error: {e}")
        return redirect(url_for('auth.signin'))


# <----------------- appointments ----------------------->
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
            patient_id=session.get('user_id'),
            doctor_id=doctor_id,
            date=appointment_date,
            time=appointment_time,
            status='Scheduled',
            notes=notes
        )
        db.session.add(new_appointment)

        # Update the doctor's is_scheduled flag
        doctor = Doctor.query.get(doctor_id)
        if doctor:
            doctor.is_scheduled = True

        db.session.commit()
        flash('Appointment made successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error making appointment.', 'error')
        print(f"Appointment creation error: {e}")

    return redirect(url_for('client.appointments'))

@bp.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))

    try:
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            # Reset the is_scheduled flag for the doctor
            doctor = Doctor.query.get(appointment.doctor_id)
            if doctor:
                doctor.is_scheduled = False

            db.session.delete(appointment)
            db.session.commit()
            flash('Appointment canceled successfully.', 'success')
        else:
            flash('Appointment not found.', 'error')
    except Exception as e:
        db.session.rollback()
        flash('Error canceling appointment.', 'error')
        print(f"Appointment cancellation error: {e}")

    return redirect(url_for('client.appointments'))

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


@bp.route('/messages')
def messages():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    return render_template('clients/messages.html')

