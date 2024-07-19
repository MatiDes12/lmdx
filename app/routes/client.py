from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Patient, Appointment, Message, LabResult, Medication
from .. import sqlalchemy_db as db
from datetime import datetime

bp = Blueprint('client', __name__)

@bp.route('/dashboard')
def dashboard():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))

    return render_template('clients/dashboard.html')



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
    
    doctor_id = request.form['doctor_id']
    date = request.form['date']
    time = request.form['time']
    notes = request.form['notes']
    
    patient_id = session.get('user_id')  # Fetch user ID from session
    if not patient_id:
        flash('User ID not found in session', 'error')
        return redirect(url_for('client.appointments'))
    
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        date=datetime.strptime(date, '%Y-%m-%d'),
        time=datetime.strptime(time, '%H:%M').time(),
        notes=notes,
        status='Scheduled'
    )
    
    try:
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating appointment: {str(e)}', 'error')
    
    return redirect(url_for('client.appointments'))


@bp.route('/messages')
def messages():
    if 'user' not in session or session.get('user_type') != 'client':
        return redirect(url_for('auth.signin'))
    return render_template('clients/messages.html')
