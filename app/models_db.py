from app import sqlalchemy_db as db
from datetime import datetime

# import logging
# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum('patient', 'doctors', 'staff', 'admin', 'organization', name='user_type_enum'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Role(db.Model):
    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)

class Permission(db.Model):
    permission_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    permission_name = db.Column(db.String(100), unique=True, nullable=False)

class UserRole(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.role_id'), primary_key=True)

class RolePermission(db.Model):
    role_id = db.Column(db.Integer, db.ForeignKey('role.role_id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.permission_id'), primary_key=True)

class AuditLog(db.Model):
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Visit(db.Model):
    visit_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'))
    doctor_name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text)
    next_steps = db.Column(db.Text)

class ClientAccounts(db.Model):
    __tablename__ = 'client_accounts'
    client_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'client'
    }
    type = db.Column(db.String(50), nullable=False)

class Patient(ClientAccounts):
    __tablename__ = 'patients'
    patient_id = db.Column(db.Integer, db.ForeignKey('client_accounts.client_id'), primary_key=True)
    dob = db.Column(db.Date)
    insurance_number = db.Column(db.String(100))
    gender = db.Column(db.Enum('Male', 'Female', 'Other', name='gender_enum'))

    __mapper_args__ = {
        'polymorphic_identity': 'patient'
    }

class Doctor(db.Model):
    __tablename__ = 'doctors'
    doctor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    phone_number = db.Column(db.String(20))
    status = db.Column(db.String(20))
    schedule = db.Column(db.String(100))
    time = db.Column(db.String(100))

class Staff(db.Model):
    staff_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)

class Appointment(db.Model):
    appointment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))  # Ensure this matches the actual table name
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum('Scheduled', 'Completed', 'Cancelled', name='appointment_status_enum'), default='Scheduled')
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)


class LabTest(db.Model):
    test_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

class LabResult(db.Model):
    result_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    test_id = db.Column(db.Integer, db.ForeignKey('lab_test.test_id'))
    result_value = db.Column(db.Text, nullable=False)
    result_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)

class InsuranceProvider(db.Model):
    provider_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    provider_name = db.Column(db.String(255), nullable=False)
    contact_info = db.Column(db.Text)

class PatientInsurance(db.Model):
    patient_insurance_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'))  # Ensure this references the polymorphic 'patients' table correctly
    provider_id = db.Column(db.Integer, db.ForeignKey('insurance_provider.provider_id'))
    policy_number = db.Column(db.String(100), nullable=False)
    coverage_details = db.Column(db.Text)


class Billing(db.Model):
    billing_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'))
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.appointment_id'))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    billing_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('Pending', 'Paid', 'Overdue', name='billing_status_enum'), default='Pending')

class Inventory(db.Model):
    inventory_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    supplier = db.Column(db.String(255))
    last_restocked = db.Column(db.Date)

class Medication(db.Model):
    medication_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    dosage = db.Column(db.String(100))
    manufacturer = db.Column(db.String(255))

class Reminder(db.Model):
    reminder_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.medication_id'))
    time = db.Column(db.Time, nullable=False)
    medication = db.relationship('Medication', backref=db.backref('reminders', lazy=True))

class Prescription(db.Model):
    prescription_id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.medication_id'))
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)

class Room(db.Model):
    room_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    room_type = db.Column(db.Enum('Ward', 'Private', 'ICU', 'Operating', name='room_type_enum'), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum('Available', 'Occupied', 'Maintenance', name='room_status_enum'), default='Available')

class PatientRoom(db.Model):
    patient_room_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'))
    room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'))
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date)


# class Message(db.Model):
#     __tablename__ = 'messages'
#     message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     sender_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
#     recipient_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
#     subject = db.Column(db.String(255))
#     body = db.Column(db.Text)
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    conversation_id = db.Column(db.String(255), unique=True, nullable=False)
    conversation_data = db.Column(db.JSON, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)




class Organization(db.Model):
    __tablename__ = 'organization'
    org_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), unique=True)
    contact_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    special_email = db.Column(db.String(255), unique=True, nullable=True)
    organization = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __init__(self, user_id, contact_name, email, organization, phone_number, state, department, special_email, license_number):
        self.user_id = user_id
        self.contact_name = contact_name
        self.email = email
        self.special_email = special_email
        self.organization = organization
        self.phone_number = phone_number
        self.state = state
        self.department = department
        self.license_number = license_number
