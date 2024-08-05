"""empty message

<<<<<<<< HEAD:migrations/versions/779d42953b66_.py
Revision ID: 779d42953b66
Revises: 
Create Date: 2024-08-05 01:04:08.194658
========
Revision ID: 67794b09b52a
Revises: 
Create Date: 2024-08-04 02:18:33.811154
>>>>>>>> 10eca5349da7caac455e671ea9bc7984d591f2e5:migrations/versions/67794b09b52a_.py

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
<<<<<<<< HEAD:migrations/versions/779d42953b66_.py
revision = '779d42953b66'
========
revision = '67794b09b52a'
>>>>>>>> 10eca5349da7caac455e671ea9bc7984d591f2e5:migrations/versions/67794b09b52a_.py
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('budget_category',
    sa.Column('category_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('allocated', sa.Float(), nullable=False),
    sa.Column('spent', sa.Float(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('category_id')
    )
    op.create_table('client_accounts',
    sa.Column('client_id', sa.String(length=255), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('client_id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('department',
    sa.Column('department_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('head', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('department_id')
    )
    op.create_table('doctors',
    sa.Column('doctor_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('specialization', sa.String(length=100), nullable=False),
    sa.Column('license_number', sa.String(length=50), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('schedule', sa.String(length=100), nullable=True),
    sa.Column('time', sa.String(length=100), nullable=True),
    sa.PrimaryKeyConstraint('doctor_id'),
    sa.UniqueConstraint('license_number')
    )
    op.create_table('facilities',
    sa.Column('facility_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=False),
    sa.Column('status', sa.Enum('Operational', 'Maintenance', 'Closed', name='facility_status_enum'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('facility_id')
    )
    op.create_table('insurance_provider',
    sa.Column('provider_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('provider_name', sa.String(length=255), nullable=False),
    sa.Column('contact_info', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('provider_id')
    )
    op.create_table('inventory',
    sa.Column('inventory_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('item_name', sa.String(length=255), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('supplier', sa.String(length=255), nullable=True),
    sa.Column('last_restocked', sa.Date(), nullable=True),
    sa.PrimaryKeyConstraint('inventory_id')
    )
    op.create_table('lab_test',
    sa.Column('test_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('test_name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('test_id')
    )
    op.create_table('medication',
    sa.Column('medication_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('dosage', sa.String(length=100), nullable=True),
    sa.Column('manufacturer', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('medication_id')
    )
    op.create_table('permission',
    sa.Column('permission_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('permission_name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('permission_id'),
    sa.UniqueConstraint('permission_name')
    )
    op.create_table('revenue',
    sa.Column('revenue_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('source', sa.String(length=255), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('date_received', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('revenue_id')
    )
    op.create_table('role',
    sa.Column('role_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('role_name', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('role_id'),
    sa.UniqueConstraint('role_name')
    )
    op.create_table('room',
    sa.Column('room_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('room_number', sa.String(length=20), nullable=False),
    sa.Column('room_type', sa.Enum('Ward', 'Private', 'ICU', 'Operating', name='room_type_enum'), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('Available', 'Occupied', 'Maintenance', name='room_status_enum'), nullable=True),
    sa.PrimaryKeyConstraint('room_id'),
    sa.UniqueConstraint('room_number')
    )
    op.create_table('user',
    sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('user_type', sa.Enum('patient', 'doctors', 'staff', 'admin', 'organization', name='user_type_enum'), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('account',
    sa.Column('id', sa.String(length=255), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('password', sa.String(length=255), nullable=False),
    sa.Column('plain_password', sa.String(length=255), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('appointment',
    sa.Column('appointment_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('client_id', sa.String(length=255), nullable=True),
    sa.Column('doctor_id', sa.Integer(), nullable=True),
    sa.Column('appointment_date', sa.Date(), nullable=False),
    sa.Column('appointment_time', sa.Time(), nullable=False),
    sa.Column('status', sa.Enum('Scheduled', 'Completed', 'Cancelled', name='appointment_status_enum'), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['client_accounts.client_id'], ),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.PrimaryKeyConstraint('appointment_id')
    )
    op.create_table('audit_log',
    sa.Column('log_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=255), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('log_id')
    )
    op.create_table('compliance',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('last_updated', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('messages',
    sa.Column('message_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('sender_id', sa.String(length=255), nullable=True),
    sa.Column('recipient_id', sa.String(length=255), nullable=True),
    sa.Column('body', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['recipient_id'], ['user.user_id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('message_id')
    )
    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.String(length=255), nullable=False),
    sa.Column('message', sa.String(length=255), nullable=False),
    sa.Column('notification_type', sa.String(length=50), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('organization',
    sa.Column('org_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('contact_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('special_email', sa.String(length=255), nullable=True),
    sa.Column('organization', sa.String(length=100), nullable=False),
    sa.Column('phone_number', sa.String(length=20), nullable=True),
    sa.Column('state', sa.String(length=100), nullable=True),
    sa.Column('department', sa.String(length=100), nullable=True),
    sa.Column('license_number', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('org_id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('license_number'),
    sa.UniqueConstraint('special_email'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('patients',
    sa.Column('patient_id', sa.String(length=255), nullable=False),
    sa.Column('dob', sa.Date(), nullable=True),
    sa.Column('insurance_number', sa.String(length=100), nullable=True),
    sa.Column('gender', sa.Enum('Male', 'Female', 'Other', name='gender_enum'), nullable=True),
    sa.Column('doctor_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['client_accounts.client_id'], ),
    sa.PrimaryKeyConstraint('patient_id')
    )
    op.create_table('prescription',
    sa.Column('prescription_id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=True),
    sa.Column('medication_id', sa.Integer(), nullable=True),
    sa.Column('dosage', sa.String(length=100), nullable=False),
    sa.Column('frequency', sa.String(length=100), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.ForeignKeyConstraint(['medication_id'], ['medication.medication_id'], ),
    sa.PrimaryKeyConstraint('prescription_id')
    )
    op.create_table('projects',
    sa.Column('project_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('status', sa.Enum('Active', 'Completed', 'On Hold', name='project_status_enum'), nullable=True),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['department.department_id'], ),
    sa.PrimaryKeyConstraint('project_id')
    )
    op.create_table('reminder',
    sa.Column('reminder_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('medication_id', sa.Integer(), nullable=True),
    sa.Column('time', sa.Time(), nullable=False),
    sa.ForeignKeyConstraint(['medication_id'], ['medication.medication_id'], ),
    sa.PrimaryKeyConstraint('reminder_id')
    )
    op.create_table('role_permission',
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('permission_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permission.permission_id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['role.role_id'], ),
    sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    op.create_table('settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('language', sa.String(length=20), nullable=True),
    sa.Column('timezone', sa.String(length=20), nullable=True),
    sa.Column('dark_mode', sa.Boolean(), nullable=True),
    sa.Column('default_patient_view', sa.String(length=20), nullable=True),
    sa.Column('show_inactive_patients', sa.Boolean(), nullable=True),
    sa.Column('records_per_page', sa.Integer(), nullable=True),
    sa.Column('default_specialization_filter', sa.String(length=50), nullable=True),
    sa.Column('show_doctor_schedules', sa.Boolean(), nullable=True),
    sa.Column('default_chart_type', sa.String(length=20), nullable=True),
    sa.Column('auto_refresh_analytics', sa.Boolean(), nullable=True),
    sa.Column('refresh_interval', sa.Integer(), nullable=True),
    sa.Column('email_notifications', sa.Boolean(), nullable=True),
    sa.Column('sms_notifications', sa.Boolean(), nullable=True),
    sa.Column('notification_frequency', sa.String(length=20), nullable=True),
    sa.Column('two_factor_auth', sa.Boolean(), nullable=True),
    sa.Column('session_timeout', sa.Integer(), nullable=True),
    sa.Column('password_expiry', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('staff',
    sa.Column('staff_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('position', sa.String(length=100), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('staff_id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('user_role',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['role.role_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    op.create_table('billing',
    sa.Column('billing_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=True),
    sa.Column('appointment_id', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('billing_date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('Pending', 'Paid', 'Overdue', name='billing_status_enum'), nullable=True),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointment.appointment_id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.PrimaryKeyConstraint('billing_id')
    )
    op.create_table('follow_up_actions',
    sa.Column('action_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('patient_id', sa.String(length=255), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('action_text', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.PrimaryKeyConstraint('action_id')
    )
    op.create_table('lab_result',
    sa.Column('result_id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=True),
    sa.Column('doctor_id', sa.Integer(), nullable=True),
    sa.Column('test_id', sa.Integer(), nullable=True),
    sa.Column('result_value', sa.Text(), nullable=False),
    sa.Column('result_date', sa.Date(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('report_type', sa.String(length=50), nullable=True),
    sa.Column('image_path', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.ForeignKeyConstraint(['test_id'], ['lab_test.test_id'], ),
    sa.PrimaryKeyConstraint('result_id')
    )
    op.create_table('organization_doctor',
    sa.Column('org_doctor_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('doctor_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.doctor_id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organization.org_id'], ),
    sa.PrimaryKeyConstraint('org_doctor_id')
    )
    op.create_table('organization_patient',
    sa.Column('org_patient_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('patient_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organization.org_id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.PrimaryKeyConstraint('org_patient_id')
    )
    op.create_table('organization_staff',
    sa.Column('org_staff_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('staff_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organization.org_id'], ),
    sa.ForeignKeyConstraint(['staff_id'], ['staff.staff_id'], ),
    sa.PrimaryKeyConstraint('org_staff_id')
    )
    op.create_table('patient_insurance',
    sa.Column('patient_insurance_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=True),
    sa.Column('provider_id', sa.Integer(), nullable=True),
    sa.Column('policy_number', sa.String(length=100), nullable=False),
    sa.Column('coverage_details', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.ForeignKeyConstraint(['provider_id'], ['insurance_provider.provider_id'], ),
    sa.PrimaryKeyConstraint('patient_insurance_id')
    )
    op.create_table('patient_room',
    sa.Column('patient_room_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=True),
    sa.Column('room_id', sa.Integer(), nullable=True),
    sa.Column('check_in_date', sa.Date(), nullable=False),
    sa.Column('check_out_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.ForeignKeyConstraint(['room_id'], ['room.room_id'], ),
    sa.PrimaryKeyConstraint('patient_room_id')
    )
    op.create_table('visits',
    sa.Column('visit_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('patient_id', sa.String(length=255), nullable=True),
    sa.Column('doctor_name', sa.String(length=255), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('next_steps', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ),
    sa.PrimaryKeyConstraint('visit_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('visits')
    op.drop_table('patient_room')
    op.drop_table('patient_insurance')
    op.drop_table('organization_staff')
    op.drop_table('organization_patient')
    op.drop_table('organization_doctor')
    op.drop_table('lab_result')
    op.drop_table('follow_up_actions')
    op.drop_table('billing')
    op.drop_table('user_role')
    op.drop_table('staff')
    op.drop_table('settings')
    op.drop_table('role_permission')
    op.drop_table('reminder')
    op.drop_table('projects')
    op.drop_table('prescription')
    op.drop_table('patients')
    op.drop_table('organization')
    op.drop_table('notifications')
    op.drop_table('messages')
    op.drop_table('compliance')
    op.drop_table('audit_log')
    op.drop_table('appointment')
    op.drop_table('account')
    op.drop_table('user')
    op.drop_table('room')
    op.drop_table('role')
    op.drop_table('revenue')
    op.drop_table('permission')
    op.drop_table('medication')
    op.drop_table('lab_test')
    op.drop_table('inventory')
    op.drop_table('insurance_provider')
    op.drop_table('facilities')
    op.drop_table('doctors')
    op.drop_table('department')
    op.drop_table('client_accounts')
    op.drop_table('budget_category')
    # ### end Alembic commands ###
