from datetime import datetime
from flask import redirect, render_template, request, session, url_for
from . import main
from ..models import Patient, Doctor, Appointment
from .. import db

@main.route('/')
def index():
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    total_patients = len(patients)
    new_patients = len([p for p in patients if p.admission_date.date() == datetime.utcnow().date()])
    admitted_patients = len([p for p in patients if p.status == 'Admitted'])
    critical_cases = len([p for p in patients if p.status == 'Critical'])

    return render_template('doctors/dashboard.html', 
                           patients=patients, 
                           doctors=doctors, 
                           total_patients=total_patients, 
                           new_patients=new_patients, 
                           admitted_patients=admitted_patients, 
                           critical_cases=critical_cases)



