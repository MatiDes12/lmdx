from datetime import datetime
from . import sqlalchemy_db as db

class DoctorAccounts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    special_email = db.Column(db.String(120), unique=True, nullable=False)
    organization = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)  # Optional phone number

    def __repr__(self):
        return f'<Doctor {self.full_name} | Email: {self.email} | Special Email: {self.special_email} | Organization: {self.organization} | Phone: {self.phone_number}>'

class ClientAccounts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)  # Optional phone number

    def __repr__(self):
        return f'<Client {self.first_name} {self.last_name} | Email: {self.email} | Phone: {self.phone_number}>'

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100))
    status = db.Column(db.String(20))
    schedule = db.Column(db.String(100))
    time = db.Column(db.String(100))
    is_scheduled = db.Column(db.Boolean, default=False)  # New field to track scheduling

    patients = db.relationship('Patient', backref='doctor', lazy=True)
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

    def __repr__(self):
        return f'<Doctor {self.name}>'

    def get_active_appointment(self):
        return next((appt for appt in self.appointments if appt.status == 'Scheduled'), None)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Scheduled')
    notes = db.Column(db.String(200))

    
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    blood_type = db.Column(db.String(3))
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    admission_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_visit = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True)
    medical_history = db.Column(db.Text)
    phone_number = db.Column(db.String(20))

    appointments = db.relationship('Appointment', backref='patient', lazy=True)

    def __repr__(self):
        return f'<Patient {self.name}>'



class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    message_type = db.Column(db.String(10), nullable=False)  # 'email' or 'sms'
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'sent' or 'failed'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship('Patient', backref='messages')

class Vitals(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    blood_pressure = db.Column(db.String(20))
    heart_rate = db.Column(db.Integer)
    respiratory_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    oxygen_saturation = db.Column(db.Integer)

    def __repr__(self):
        return f'<Vitals {self.id}>'

class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Medication {self.id}>'

class LabResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    test_name = db.Column(db.String(100), nullable=False)
    result_value = db.Column(db.String(100), nullable=False)
    units = db.Column(db.String(20))
    reference_range = db.Column(db.String(100))
    date_conducted = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<LabResult {self.id}>'

class Surgery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    surgery_name = db.Column(db.String(100), nullable=False)
    surgery_date = db.Column(db.DateTime, nullable=False)
    surgeon_name = db.Column(db.String(100))
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Surgery {self.id}>'
