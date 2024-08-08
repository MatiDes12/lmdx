from app import sqlalchemy_db as db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import generate_password_hash, check_password_hash

# import logging
# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=False, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum('patient', 'doctors', 'staff', 'admin', 'organization', name='user_type_enum'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    settings = db.relationship('Settings', backref='user', uselist=False)
    firebase_uid = db.Column(db.String(255), nullable=False, unique=False)

    def set_password(self, password):
        """Generate a BCrypt hash for the password."""
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

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

class FollowUpAction(db.Model):
    __tablename__ = 'follow_up_actions'
    action_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    action_text = db.Column(db.String(255))
    patient = db.relationship('Patient', back_populates='follow_up_actions')

class Visit(db.Model):
    __tablename__ = 'visits'
    visit_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text)
    next_steps = db.Column(db.Text)
    patient = db.relationship('Patient', back_populates='visits')

class ClientAccounts(db.Model):
    __tablename__ = 'client_accounts'
    client_id = db.Column(db.String(255), primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False)

    __mapper_args__ = {
        'polymorphic_on': 'type',
        'polymorphic_identity': 'client'
    }

class Patient(db.Model):
    __tablename__ = 'patients'
    patient_id = db.Column(db.String(255), db.ForeignKey('client_accounts.client_id'), primary_key=True)
    dob = db.Column(db.Date)
    insurance_number = db.Column(db.String(100))
    gender = db.Column(db.Enum('Male', 'Female', 'Other', name='gender_enum'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    visits = db.relationship('Visit', back_populates='patient')
    follow_up_actions = db.relationship('FollowUpAction', back_populates='patient')
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))  # Foreign key to reference a Doctor
    image_path = db.Column(db.String(255)) 

    doctor = db.relationship('Doctor', backref=db.backref('patients', lazy=True))




class Compliance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'), nullable=False)  # Corrected ForeignKey reference
    status = db.Column(db.String(20), nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    doctor = db.relationship('Doctor', backref=db.backref('compliance', lazy=True))

class Account(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    plain_password = db.Column(db.String(255), nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)

    doctor = db.relationship('Doctor', backref=db.backref('accounts', lazy=True))


class Doctor(db.Model):
    __tablename__ = 'doctors'
    doctor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    phone_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Inactive', nullable=False)
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
    client_id = db.Column(db.String(255), db.ForeignKey('client_accounts.client_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))  # Ensure this matches the actual table name
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum('Scheduled', 'Completed', 'Cancelled', 'Pending', name='appointment_status_enum'), default='Scheduled')
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    doctor = db.relationship('Doctor', backref='appointments')
    client = db.relationship('ClientAccounts', backref='appointments')

class LabTest(db.Model):
    __tablename__ = 'lab_test'
    test_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

class LabResult(db.Model):
    __tablename__ = 'lab_result'
    result_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('client_accounts.client_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    test_id = db.Column(db.Integer, db.ForeignKey('lab_test.test_id'))
    result_value = db.Column(db.Text, nullable=False)
    result_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    image_path = db.Column(db.String(255)) 

    patient = db.relationship('ClientAccounts', backref=db.backref('lab_results', lazy=True))
    doctor = db.relationship('Doctor', backref=db.backref('lab_results', lazy=True))
    test = db.relationship('LabTest', backref=db.backref('lab_results', lazy=True))



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
    client_id = db.Column(db.String(255), db.ForeignKey('client_accounts.client_id'))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    dosage = db.Column(db.String(100))
    manufacturer = db.Column(db.String(255))

class Reminder(db.Model):
    reminder_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    medication_id = db.Column(db.String(255), db.ForeignKey('medication.medication_id'))
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.prescription_id'))
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    time = db.Column(db.Time, nullable=False)
    taken = db.Column(db.Boolean, default=False)  # Add this field
    repeat = db.Column(db.Boolean, default=False)  # Add this field
    
    medication = db.relationship('Medication', backref=db.backref('reminders', lazy=True))
    prescription = db.relationship('Prescription', backref=db.backref('reminders', lazy=True))


class Prescription(db.Model):
    prescription_id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    patient_id = db.Column(db.String(255), db.ForeignKey('client_accounts.client_id'))  # Add this foreign key
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.medication_id'), nullable=False)  
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)

    doctor = db.relationship('Doctor', backref='prescriptions')
    patient = db.relationship('ClientAccounts', backref='prescriptions')  # Correct the relationship
    medication = db.relationship('Medication', backref='prescriptions')  # Add this relationship

    
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

class BloodTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    test_type = db.Column(db.String(255))  # e.g., "Comprehensive Metabolic Panel"
    test_date = db.Column(db.Date, default=datetime.utcnow)
    results = db.Column(db.JSON)  # Storing results as a JSON object

    patient = db.relationship('Patient', backref='blood_tests')
    doctor = db.relationship('Doctor', backref='ordered_tests')


class VitalSign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    date = db.Column(db.Date, default=datetime.utcnow)
    time = db.Column(db.Time, default=datetime.utcnow)
    temperature = db.Column(db.Float)
    pulse = db.Column(db.Integer)
    blood_pressure = db.Column(db.String(20))  # e.g., "120/80"
    respiratory_rate = db.Column(db.Integer)
    oxygen_saturation = db.Column(db.Integer)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    bmi = db.Column(db.Float)

    patient = db.relationship('Patient', backref='vital_signs')
    doctor = db.relationship('Doctor', backref='recorded_signs')


class MedicalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    date = db.Column(db.Date, default=datetime.utcnow)
    medical_condition = db.Column(db.String(255))
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref='medical_history')
    doctor = db.relationship('Doctor', backref='recorded_history')


class Procedure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    date = db.Column(db.Date, default=datetime.utcnow)
    procedure_name = db.Column(db.String(255))
    description = db.Column(db.Text)
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref='procedures')
    doctor = db.relationship('Doctor', backref='performed_procedures')

class Admission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'))
    admission_date = db.Column(db.Date, default=datetime.utcnow)
    discharge_date = db.Column(db.Date)
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref='admissions')
    doctor = db.relationship('Doctor', backref='admissions')
    room = db.relationship('Room', backref='admissions')

class Discharge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('admission.id'))
    discharge_date = db.Column(db.Date, default=datetime.utcnow)
    discharge_notes = db.Column(db.Text)

    admission = db.relationship('Admission', backref='discharge')

class Surgery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'))
    surgery_date = db.Column(db.Date, default=datetime.utcnow)
    procedure_name = db.Column(db.String(255))
    description = db.Column(db.Text)
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref='surgeries')
    doctor = db.relationship('Doctor', backref='performed_surgeries')
    room = db.relationship('Room', backref='surgeries')

class DischargeSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('admission.id'))
    discharge_date = db.Column(db.Date, default=datetime.utcnow)
    discharge_notes = db.Column(db.Text)

    admission = db.relationship('Admission', backref='discharge_summary')

class Transfer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(255), db.ForeignKey('patients.patient_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))
    room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'))
    transfer_date = db.Column(db.Date, default=datetime.utcnow)
    from_room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'))
    to_room_id = db.Column(db.Integer, db.ForeignKey('room.room_id'))
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)

    patient = db.relationship('Patient', backref='transfers')
    doctor = db.relationship('Doctor', backref='transfers')
    from_room = db.relationship('Room', foreign_keys=[from_room_id], primaryjoin='Transfer.from_room_id == Room.room_id')
    to_room = db.relationship('Room', foreign_keys=[to_room_id], primaryjoin='Transfer.to_room_id == Room.room_id')




class Facility(db.Model):
    __tablename__ = 'facilities'
    facility_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('Operational', 'Maintenance', 'Closed', name='facility_status_enum'), nullable=False, default='Operational')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.String(255), db.ForeignKey('user.user_id'))
    recipient_id = db.Column(db.String(255), db.ForeignKey('user.user_id'))
    body = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class Department(db.Model):
    __tablename__ = 'department'
    department_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    head = db.Column(db.String(100), nullable=False)



class Project(db.Model):
    __tablename__ = 'projects'
    
    project_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.Enum('Active', 'Completed', 'On Hold', name='project_status_enum'), default='Active')
    department_id = db.Column(db.Integer, db.ForeignKey('department.department_id'), nullable=False)
    
    # Relationship
    department = db.relationship('Department', backref=db.backref('projects', lazy=True))

    def __repr__(self):
        return f'<Project {self.name}>'
    


class BudgetCategory(db.Model):
    __tablename__ = 'budget_category'
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    allocated = db.Column(db.Float, nullable=False, default=0.0)
    spent = db.Column(db.Float, nullable=False, default=0.0)
    description = db.Column(db.Text, nullable=True)

    def __init__(self, name, allocated, spent=0.0, description=None):
        self.name = name
        self.allocated = allocated
        self.spent = spent
        self.description = description

class Revenue(db.Model):
    __tablename__ = 'revenue'
    revenue_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_received = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


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

class OrganizationStaff(db.Model):
    org_staff_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.org_id'))
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.staff_id'))


class OrganizationDoctor(db.Model):
    org_doctor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.org_id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'))


class OrganizationPatient(db.Model):
    org_patient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.org_id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'))


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    language = db.Column(db.String(20), default='en')
    timezone = db.Column(db.String(20), default='UTC')
    dark_mode = db.Column(db.Boolean, default=False)
    default_patient_view = db.Column(db.String(20), default='list')
    show_inactive_patients = db.Column(db.Boolean, default=False)
    records_per_page = db.Column(db.Integer, default=20)
    default_specialization_filter = db.Column(db.String(50), default='all')
    show_doctor_schedules = db.Column(db.Boolean, default=False)
    default_chart_type = db.Column(db.String(20), default='bar')
    auto_refresh_analytics = db.Column(db.Boolean, default=False)
    refresh_interval = db.Column(db.Integer, default=5)
    email_notifications = db.Column(db.Boolean, default=False)
    sms_notifications = db.Column(db.Boolean, default=False)
    notification_frequency = db.Column(db.String(20), default='immediately')
    two_factor_auth = db.Column(db.Boolean, default=False)
    session_timeout = db.Column(db.Integer, default=30)
    password_expiry = db.Column(db.Integer, default=90)

class Notification(db.Model):
    __tablename__ = 'notifications' 
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.doctor_id'), nullable=False)
    patient_id = db.Column(db.String(255), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)  # New column to track read status

    doctor = db.relationship('Doctor', backref=db.backref('notifications', lazy=True))


