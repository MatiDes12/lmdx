
from mailbox import Message
from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from ..models_db import Doctor, Patient, Appointment, User
from .. import sqlalchemy_db as db
from datetime import datetime
from app.routes.auth import firebase_db
from werkzeug.utils import secure_filename


bp = Blueprint('patient', __name__)

@bp.route('/dashboard')
def dashboard():
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
            print(first_name, last_name)
            return render_template('clients/dashboard.html', first_name=first_name, last_name=last_name)
        else:
            flash('Unable to fetch user details.', 'error')
            return redirect(url_for('auth.signin'))
    except Exception as e:
        flash('Error accessing user information.', 'error')
        print(f"Firebase fetch error: {e}")
        return redirect(url_for('auth.signin'))
    
@bp.route('/fetch_user_info')
def fetch_user_info():
    try:
        user_id = session.get('user_id')
        if not user_id:
            raise ValueError("User ID not found in session")

        user_info = User.query.filter_by(id=user_id).first()
        if not user_info:
            raise ValueError("No user found with the given ID")

        return render_template('user_info.html', user=user_info)

    except Exception as e:
        # Log the error for further investigation
        print(f"Error accessing user information: {e}")
        flash('Error accessing user information.', 'error')
        return redirect(url_for('auth.login'))  # Redirect to login or appropriate error page


#<-------------------------- appointments -------------------------------->
@bp.route('/appointments', methods=['GET'])
def appointments():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    doctors = Doctor.query.all()
    return render_template('clients/appointments.html', doctors=doctors)

@bp.route('/make_appointment', methods=['POST'])
def make_appointment():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    
    user_id = session.get('user_id')  # Make sure 'user_id' is stored in session during the sign-in process
    doctor_id = request.form.get('doctor_id')
    date = request.form.get('date')
    time = request.form.get('time')
    notes = request.form.get('notes', '')
    
    if not all([doctor_id, date, time]):
        flash('All fields are required.', 'error')
        return redirect(url_for('patient.appointments'))

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
    
    return redirect(url_for('patient.dashboard'))


#<-------------------------- messages -------------------------------->

@bp.route('/messages', methods=['GET'])
def messages():
    if 'user' not in session or session.get('user_type') not in ['patient', 'client']:
        return redirect(url_for('auth.signin'))

    # Fetch doctors
    doctors = Doctor.query.all()
    doctor_statuses = []
    for doctor in doctors:
        user = User.query.get(doctor.doctor_id)
        status = 'Active' if user else 'Inactive'
        doctor_statuses.append({
            'id': doctor.doctor_id,
            'name': f"{doctor.first_name} {doctor.last_name}",
            'specialization': doctor.specialization,
            'status': status
        })

    # Fetch messages sent to the current client from doctors
    client_id = session.get('user_id')
    messages = Message.query.filter_by(recipient_id=client_id).all()

    # Fetch the sender information for each message
    message_details = []
    for message in messages:
        sender = User.query.get(message.sender_id)
        doctor = Doctor.query.filter_by(doctor_id=sender.doctor_id).first()
        if doctor:
            message_details.append({
                'doctor_name': f"{doctor.first_name} {doctor.last_name}",
                'doctor_image': f"https://i.pravatar.cc/300?img={doctor.doctor_id % 70}",  # Random image for doctor
                'body': message.body,
                'timestamp': message.timestamp
            })

    # Add a sample message from a "doctor" to yourself
    sample_message = {
        'doctor_name': 'Dr. Sample',
        'doctor_image': 'https://i.pravatar.cc/300?img=1',  # Sample image
        'body': 'This is a sample message from Dr. Sample.',
        'timestamp': datetime.utcnow()
    }
    message_details.append(sample_message)

    return render_template('clients/messages.html', doctor_statuses=doctor_statuses, doctors=doctor_statuses, messages=message_details)

@bp.route('/send_message', methods=['POST'])
def send_message():
    if 'user' not in session or session.get('user_type') not in ['patient', 'client']:
        return redirect(url_for('auth.signin'))

    doctor_id = request.form.get('doctor_id')
    message_body = request.form.get('message')
    sender_id = session.get('user_id')  # Assuming you store the logged-in user's ID in session

    if not doctor_id or not message_body:
        flash('Please select a doctor and enter a message.')
        return redirect(url_for('patient.messages'))

    # Assuming recipient_id is the user_id of the doctor
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        flash('Invalid doctor selected.')
        return redirect(url_for('patient.messages'))

    recipient_id = doctor.doctor_id

    # Create and save the message
    message = Message(sender_id=sender_id, recipient_id=recipient_id, subject='Message from Client', body=message_body)
    db.session.add(message)
    db.session.commit()

    flash('Message sent successfully.')
    return redirect(url_for('patient.messages'))

#<-------------------------- test results -------------------------------->

@bp.route('/test_results')
def test_results():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    return render_template('clients/test_results.html')

@bp.route('/medication')
def medication():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    return render_template('clients/medication.html')

@bp.route('/visits')
def visits():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    return render_template('clients/visits.html')


@bp.route('/billing')
def billing():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('auth.signin'))
    return render_template('clients/billing.html')

@bp.route('/insurance', methods=['GET', 'POST'])
def insurance():
    # Ensure user is logged in and has the right user type
    if 'user' not in session or session.get('user_type') != 'patient':
        flash('You must be signed in to access this page.', 'error')
        return redirect(url_for('auth.signin'))

    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file part in the request.', 'error')
            return redirect(request.url)

        if file.filename == '':
            flash('No selected file.', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            flash('File successfully uploaded.', 'success')
            return redirect(url_for('insurance'))

    return render_template('clients/insurance.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def get_health_tips():
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "llama-3-sonar-small-32k-online",
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise."
            },
            {
                "role": "user",
                "content": "Provide five daily health tips."
            }
        ]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer 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"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            raw_tips = response.json().get('choices', [])[0].get('message', {}).get('content', '').split('\n')
            tips = [markdown_to_html(tip) for tip in raw_tips if tip.strip()]
            return tips
        else:
            print(f"Failed to fetch tips, status code: {response.status_code}")
            return ["Error fetching tips: Server responded with an error."]
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return ["Error fetching tips: Failed to reach the server."]

def markdown_to_html(text):
    """Convert markdown bold syntax to HTML."""
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

@bp.route('/health_tips')
def health_tips():
    tips = get_health_tips()
    if tips:
        return render_template('clients/health_tips.html', tips=tips)
    else:
        return abort(500, description="Failed to load health tips.")

