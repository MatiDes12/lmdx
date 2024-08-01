<<<<<<< HEAD
from mailbox import Message
=======
from datetime import datetime
from mailbox import Message
import bcrypt
>>>>>>> R_Branch
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import pyrebase
from firebase_admin import auth
import requests
from app.config import Config
from app import sqlalchemy_db as db
<<<<<<< HEAD
from ..models_db import ClientAccounts, DoctorAccounts, Doctor
=======
from ..models_db import ClientAccounts, Organization, User, Account
>>>>>>> R_Branch

from flask_mail import Mail

mail = Mail()
bp = Blueprint('auth', __name__)

firebase = None  # Define firebase variable globally
firebase_db = None  # Define firebase database globally

def initialize_firebase():
    global firebase, firebase_db
    firebase = pyrebase.initialize_app(Config.FIREBASE_CONFIG)
    firebase_db = firebase.database()

# Initialize firebase app
initialize_firebase()

<<<<<<< HEAD
=======
# app/routes/auth.py

>>>>>>> R_Branch
@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    user_type = request.args.get('type', 'patient')  # Default to 'patient' if not specified
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone_number = request.form['phone_number']

        if password != confirm_password:
            return render_template('auth/signup.html', user_type=user_type) + '''
                <script>
                    showFlashMessage('Passwords do not match.', 'red');
                </script>
            '''
        elif len(password) < 8:
            return render_template('auth/signup.html', user_type=user_type) + '''
                <script>
                    showFlashMessage('Password must be at least 8 characters long.', 'red');
                </script>
            '''
<<<<<<< HEAD
=======
        elif User.query.filter_by(email=email).first():
            return render_template('auth/signup.html', user_type=user_type) + '''
                <script>
                    showFlashMessage('The email address is already in Use.', 'red', 'Error');
                </script>
            '''
>>>>>>> R_Branch

        if user_type == 'organization':
            name = request.form['name']
            org_name = request.form['org_name']
            state = request.form['state']
            license_number = request.form['license_number']
            if not name or len(name) < 6:
                return render_template('auth/signup.html', user_type=user_type) + '''
                    <script>
                        showFlashMessage('Username must be at least 6 characters long for doctors.', 'red');
                    </script>
                '''
<<<<<<< HEAD
            user_data = {'full_name': name, 'email': email, 'organization': org_name, 'phone_number': phone_number}
        else:
=======
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_user = User(username=name, email=email, password_hash=hashed_password, user_type=user_type, created_at=datetime.now())
            db.session.add(new_user)
            db.session.commit()
            user_data = {'full_name': name, 'email': email, 'organization': org_name, 'phone_number': phone_number}
        elif user_type == 'patient':
>>>>>>> R_Branch
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            if not first_name or not last_name or len(first_name) < 2 or len(last_name) < 2:
                return render_template('auth/signup.html', user_type=user_type) + '''
                    <script>
                        showFlashMessage('Both first name and last name are required for clients and must be at least 2 characters long.', 'red');
                    </script>
                '''
            user_data = {'first_name': first_name, 'last_name': last_name, 'email': email, 'phone_number': phone_number}
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_user = User(username=first_name + " " + last_name, email=email, password_hash=hashed_password, user_type=user_type, created_at=datetime.now())
            db.session.add(new_user)
            db.session.commit()

        try:
            # Check if the email already exists
            try:
                existing_user = firebase.auth().get_account_info(email)
                return render_template('auth/signup.html', user_type=user_type) + '''
                    <script>
                        showFlashMessage('The email address is already in use by another account.', 'red');
                    </script>
                '''
            except:
                # If the email does not exist, proceed to create the user
                pass

            # Create user in Firebase Authentication
            user = firebase.auth().create_user_with_email_and_password(email, password)
            id_token = user['idToken']
            refresh_token = user['refreshToken']
<<<<<<< HEAD
=======
            firebase_user_id = user['localId']
>>>>>>> R_Branch

            # Send email verification
            firebase.auth().send_email_verification(id_token)

            # Save additional data to the Firebase database based on user type
<<<<<<< HEAD
            if user_type == 'doctor':
                firebase_db.child("DoctorAccounts").child(user['localId']).set(user_data, token=id_token)

                # Create a new Doctor record in SQLAlchemy
                new_doctor = DoctorAccounts(
                    full_name=name,
                    email=email,
                    special_email=email,
                    organization=org_name,
                    phone_number=phone_number
                )
                db.session.add(new_doctor)
            else:
                firebase_db.child("ClientAccounts").child(user['localId']).set(user_data, token=id_token)

                # Create a new Client record in SQLAlchemy
                new_client = ClientAccounts(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone_number=phone_number
                )
                db.session.add(new_client)

            db.session.commit()

            session['user_type'] = user_type
            session['user_id_token'] = id_token
            session['refresh_token'] = refresh_token
            session['local_id'] = user['localId']
            session['user_data'] = user_data
            return redirect(url_for('auth.check_verification'))  # Redirect to verification check

        except Exception as e:
            db.session.rollback()
            return render_template('auth/signup.html', user_type=user_type) + f'''
                <script>
                    showFlashMessage('Error: {str(e)}', 'red');
                </script>
            '''
    return render_template('auth/signup.html', user_type=user_type)

=======
            if user_type == 'organization':
                firebase_db.child("Organization").child(firebase_user_id).set(user_data, token=id_token)
                
                try:
                    # Attempt to add the new organization to the session and commit
                    new_organization = Organization(
                        user_id=new_user.user_id,
                        contact_name=name,
                        email=email,
                        special_email=None,
                        organization=org_name,
                        phone_number=phone_number,
                        state=state,
                        department=None,
                        license_number=license_number
                    )
                    db.session.add(new_organization)
                    db.session.commit()

                    print("Organization added successfully.")
                except Exception as e:
                    print(f"Failed to add organization: {e}")
                    db.session.rollback()

            if user_type == 'patient':
                firebase_db.child("ClientAccounts").child(firebase_user_id).set(user_data, token=id_token)

                # Create a new Client record in SQLAlchemy
                new_client = ClientAccounts(
                    client_id=firebase_user_id,  # Set Firebase ID as client_id
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone_number=phone_number
                )
                db.session.add(new_client)
                db.session.commit()

            print(f"User created: {user}")
            session['user_type'] = user_type
            session['user_id_token'] = id_token
            session['refresh_token'] = refresh_token
            session['local_id'] = firebase_user_id
            session['user_data'] = user_data
            return redirect(url_for('auth.check_verification'))  # Redirect to verification check

        except Exception as e:
            db.session.rollback()
            return render_template('auth/signup.html', user_type=user_type) + f'''
                <script>
                    showFlashMessage('Error: {str(e)}', 'red');
                </script>
            '''
    return render_template('auth/signup.html', user_type=user_type)
>>>>>>> R_Branch


@bp.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print(f"Attempting sign-in for email: {email}")  # Debugging line
        
        try:
            # Attempt to sign in with the provided email and password
            user = firebase.auth().sign_in_with_email_and_password(email, password)
            id_token = user['idToken']
            refresh_token = user['refreshToken']
            user_info = firebase.auth().get_account_info(id_token)
            user_id = user_info['users'][0]['localId']

            print(f"Sign-in successful for email: {email}")  # Debugging line

            # Check if the user is a doctor
<<<<<<< HEAD
            doctor_data = firebase_db.child("DoctorAccounts").child(user_id).get(token=id_token).val()
            if doctor_data:
                user_type = 'doctor'
=======
            doctor_data = firebase_db.child("Doctors").child(user_id).get(token=id_token).val()
            if doctor_data:
                user_type = 'doctors'
>>>>>>> R_Branch
            else:
                # If not a doctor, check if it's a client
                client_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
                if client_data:
                    user_type = 'patient'
                else:
<<<<<<< HEAD
                    return render_template('auth/signin.html') + '''
                        <script>
                            showFlashMessage('Invalid email or password', 'red');
                        </script>
                    '''
=======
                    # Check if it's an organization user
                    org_data = firebase_db.child("Organization").child(user_id).get(token=id_token).val()
                    if org_data:
                        user_type = 'organization'
                    else:
                        return render_template('auth/signin.html') + '''
                            <script>
                                showFlashMessage('Invalid email or password', 'red');
                            </script>
                        '''
>>>>>>> R_Branch

            # Check if email is verified, but skip this for doctors
            email_verified = user_info['users'][0]['emailVerified']
            print("user type: ", user_type)
            if email_verified or user_type == 'doctors':
                session['user'] = email
                session['user_type'] = user_type
                session['user_id_token'] = id_token
                session['refresh_token'] = refresh_token  # Store refresh token in session
                session['user_id'] = user_id  # Store user_id in session

                if user_type == 'organization':
                    return redirect(url_for('admin.admin_dashboard'))
                elif user_type == 'patient':
                    return redirect(url_for('patient.patient_dashboard'))
                elif user_type == 'doctors':
                    return redirect(url_for('doctor.doctor_dashboard'))
            else:
                return render_template('auth/signin.html') + '''
                    <script>
<<<<<<< HEAD
                        showFlashMessage('Please verify your email before signing in.', 'yellow');
=======
                        showFlashMessage('Please verify your email before signing in.', 'yellow', 'Notice');
>>>>>>> R_Branch
                    </script>
                '''
        except Exception as e:
            # Debug: Output error
            print(f"Sign-in error: {e}")
            return render_template('auth/signin.html') + '''
                <script>
<<<<<<< HEAD
                    showFlashMessage('Invalid email or password', 'red');
=======
                    showFlashMessage('Invalid email or password', 'red', 'Error');
>>>>>>> R_Branch
                </script>
            '''
    return render_template('auth/signin.html')



@bp.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_type', None)
    session.pop('user_id_token', None)
    session.pop('refresh_token', None)
    session.pop('local_id', None)
    session.pop('user_data', None)
    return redirect(url_for('auth.signin'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        try:
            firebase.auth().send_password_reset_email(email)
            flash('Password reset email sent. Please check your inbox.', 'success')
        except Exception as e:
            flash('Error sending password reset email: ' + str(e), 'danger')
    return render_template('auth/forgot_password.html')

def refresh_id_token(refresh_token):
    try:
        refresh_url = f"https://securetoken.googleapis.com/v1/token?key={Config.FIREBASE_CONFIG['apiKey']}"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        response = requests.post(refresh_url, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error refreshing ID token: {e}")
        return None

@bp.route('/check-verification')
def check_verification():
    if 'user_id_token' not in session or 'user_type' not in session:
        flash('Please sign in to continue.', 'warning')
        return redirect(url_for('auth.signin'))

    try:
        id_token = session['user_id_token']
        user_type = session['user_type']
        local_id = session['local_id']
        user_data = session['user_data']

        refreshed_data = refresh_id_token(session['refresh_token'])
        if refreshed_data is None:
            flash('Failed to refresh ID token. Please try signing in again.', 'danger')
            return redirect(url_for('auth.signin'))

        session['user_id_token'] = refreshed_data['id_token']
        session['refresh_token'] = refreshed_data['refresh_token']

        user_info = firebase.auth().get_account_info(session['user_id_token'])
        email_verified = user_info['users'][0]['emailVerified']

        if email_verified:
<<<<<<< HEAD
            if user_type == 'doctor':
=======
            if user_type == 'organization':
>>>>>>> R_Branch
                name = user_data['full_name']
                name_parts = name.split()
                special_email = f"{name_parts[0]}.{name_parts[-1]}@lmdx.com".lower()
                special_email = special_email.replace('..', '.')

                auth.update_user(local_id, email=special_email)

                firebase_db.child("special_emails").child(local_id).set({'special_email': special_email}, token=id_token)

                send_special_email_notification(user_data['email'], special_email)
                flash(f'Please use your new email {special_email} for future logins.', 'success')
            return redirect(url_for('auth.signin'))
        else:
            return render_template('auth/check_verification.html')
    except Exception as e:
        flash(f'Error during verification check: {str(e)}', 'danger')
        return redirect(url_for('auth.signin'))

<<<<<<< HEAD
=======
from flask_mail import Mail

mail = Mail()

>>>>>>> R_Branch
def send_special_email_notification(personal_email, special_email):
    msg = Message('Your New Luminamedix Email', recipients=[personal_email])
    msg.body = f"Dear Doctor,\n\nYour new email for signing in to Luminamedix is {special_email}.\nPlease use this email for all future logins.\n\nBest regards,\nLuminamedix Team"
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return f"An error occurred while sending the email: {str(e)}"

def refresh_id_token(refresh_token):
    try:
        refresh_url = f"https://securetoken.googleapis.com/v1/token?key={Config.FIREBASE_CONFIG['apiKey']}"
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        response = requests.post(refresh_url, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error refreshing ID token: {e}")
        return None

        

@bp.route('/resend-verification-email', methods=['POST'])
def resend_verification_email():
    if 'user_id_token' not in session:
        return {'status': 'error', 'message': 'User not logged in'}, 401

    try:
        id_token = session['user_id_token']
        firebase.auth().send_email_verification(id_token)
        return {'status': 'success', 'message': 'Verification email sent'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 400
<<<<<<< HEAD


# from flask import Blueprint, render_template, request, redirect, url_for, flash, session
# from flask_mail import Message
# import pyrebase
# from firebase_admin import auth
# from app.config import Config
# from app import mail
# import requests
# from ..models_db import ClientAccounts, DoctorAccounts
# from app import mail, sqlalchemy_db as db

# bp = Blueprint('auth', __name__)

# firebase = None  # Define firebase variable globally
# firebase_db = None  # Define firebase database globally

# def initialize_firebase():
#     global firebase, firebase_db
#     firebase = pyrebase.initialize_app(Config.FIREBASE_CONFIG)
#     firebase_db = firebase.database()

# # Initialize firebase app
# initialize_firebase()

# def send_special_email_notification(personal_email, special_email):
#     msg = Message('Your New Luminamedix Email', recipients=[personal_email])
#     msg.body = f"Dear Doctor,\n\nYour new email for signing in to Luminamedix is {special_email}.\nPlease use this email for all future logins.\n\nBest regards,\nLuminamedix Team"
#     try:
#         mail.send(msg)
#         print(f"Email sent to {personal_email}")
#     except Exception as e:
#         print(f"Failed to send email: {str(e)}")
#         flash(f"An error occurred while sending the email: {str(e)}", 'danger')

# def generate_special_email(name):
#     if name:
#         name_parts = name.split()
#         special_email = f"{name_parts[0]}.{name_parts[-1]}@lmdx.com".lower()
#         special_email = special_email.replace('..', '.')
#         if special_email.endswith('.@lmdx.com'):
#             special_email = special_email[:-9] + '@lmdx.com'
#         return special_email
#     return None

# @bp.route('/signup', methods=['GET', 'POST'])
# def signup():
#     user_type = request.args.get('type', 'patient')  # Default to 'patient' if not specified
#     error = None
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         confirm_password = request.form['confirm_password']
#         phone_number = request.form['phone_number']

#         if password != confirm_password:
#             error = 'Passwords do not match.'
#         elif len(password) < 8:
#             error = 'Password must be at least 8 characters long.'

#         if user_type == 'doctor':
#             name = request.form['name']
#             org_name = request.form['org_name']
#             if not name or len(name) < 6:
#                 error = 'Username must be at least 6 characters long for doctors.'
#             special_email = generate_special_email(name)
#             if special_email is None:
#                 error = 'Could not generate a valid special email.'
#             user_data = {'full_name': name, 'email': special_email, 'organization': org_name, 'phone_number': phone_number, 'personal_email': email}

#         else:
#             first_name = request.form.get('first_name')
#             last_name = request.form.get('last_name')
#             if not first_name or not last_name or len(first_name) < 2 or len(last_name) < 2:
#                 error = 'Both first name and last name are required for clients and must be at least 2 characters long.'
#             user_data = {'first_name': first_name, 'last_name': last_name, 'email': email, 'phone_number': phone_number}

#         if error is None:
#             try:
#                 # Check if the email already exists
#                 try:
#                     existing_user = firebase.auth().get_account_info(email)
#                     error = 'The email address is already in use by another account.'
#                 except:
#                     # If the email does not exist, proceed to create the user
#                     pass
                
#                 if not error:
#                     # Create user in Firebase Authentication
#                     user = firebase.auth().create_user_with_email_and_password(email, password)
#                     id_token = user['idToken']
#                     refresh_token = user['refreshToken']
                    
#                     # Send email verification
#                     firebase.auth().send_email_verification(id_token)

#                     # Save additional data to the Firebase database based on user type
#                     if user_type == 'doctor':
#                         firebase_db.child("DoctorAccounts").child(user['localId']).set(user_data, token=id_token)
                        
#                         # Create a new Doctor record in SQLAlchemy
#                         new_doctor = DoctorAccounts(
#                             full_name=name,
#                             email=email,
#                             special_email=special_email,
#                             organization=org_name,
#                             phone_number=phone_number
#                         )
#                         db.session.add(new_doctor)
#                     else:
#                         firebase_db.child("ClientAccounts").child(user['localId']).set(user_data, token=id_token)
                        
#                         # Create a new Client record in SQLAlchemy
#                         new_client = ClientAccounts(
#                             first_name=first_name,
#                             last_name=last_name,
#                             email=email,
#                             phone_number=phone_number
#                         )
#                         db.session.add(new_client)

#                     db.session.commit()

#                     session['user_type'] = user_type
#                     session['user_id_token'] = id_token
#                     session['refresh_token'] = refresh_token
#                     session['local_id'] = user['localId']
#                     session['user_data'] = user_data
#                     return redirect(url_for('auth.check_verification'))  # Redirect to verification check

#             except Exception as e:
#                 db.session.rollback()
#                 error = str(e)
                
#     return render_template('auth/signup.html', error=error, user_type=user_type)



# @bp.route('/signin', methods=['GET', 'POST'])
# def signin():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         try:
#             # Attempt to sign in with the provided email and password
#             user = firebase.auth().sign_in_with_email_and_password(email, password)
#             id_token = user['idToken']
#             refresh_token = user['refreshToken']
#             user_info = firebase.auth().get_account_info(id_token)
#             user_id = user_info['users'][0]['localId']

#             # Debug: Output user information
#             print(f"User ID: {user_id}, Email: {email}")

#             # Check if the user is a doctor by looking up the special email
#             special_email_data = firebase_db.child("special_emails").child(user_id).get(token=id_token).val()
#             if special_email_data and special_email_data['special_email'] == email:
#                 user_type = 'doctor'
#             else:
#                 # If not a special email, check if it's a client
#                 client_data = firebase_db.child("ClientAccounts").child(user_id).get(token=id_token).val()
#                 if client_data:
#                     user_type = 'client'
#                 else:
#                     flash('Invalid email or password', 'danger')
#                     return redirect(url_for('auth.signin'))

#             # Debug: Output user type
#             print(f"User Type: {user_type}")

#             # Check if email is verified
#             email_verified = user_info['users'][0]['emailVerified']

#             if email_verified:
#                 session['user'] = email
#                 session['user_type'] = user_type
#                 session['user_id_token'] = id_token
#                 session['refresh_token'] = refresh_token  # Store refresh token in session
#                 session['user_id'] = user_id  # Store user_id in session
#                 return redirect(url_for(f'dashboard.{user_type}_dashboard'))
#             else:
#                 flash('Please verify your email before signing in.', 'warning')
#                 return redirect(url_for('auth.signin'))
#         except Exception as e:
#             # Debug: Output error
#             print(f"Sign-in error: {e}")
#             flash('Invalid email or password', 'danger')
#     return render_template('auth/signin.html')

# @bp.route('/logout')
# def logout():
#     session.pop('user', None)
#     session.pop('user_type', None)
#     session.pop('user_id_token', None)
#     session.pop('refresh_token', None)
#     session.pop('local_id', None)
#     session.pop('user_data', None)
#     return redirect(url_for('auth.signin'))

# @bp.route('/forgot-password', methods=['GET', 'POST'])
# def forgot_password():
#     if request.method == 'POST':
#         email = request.form['email']
#         try:
#             firebase.auth().send_password_reset_email(email)
#             flash('Password reset email sent. Please check your inbox.', 'success')
#         except Exception as e:
#             flash('Error sending password reset email: ' + str(e), 'danger')
#     return render_template('auth/forgot_password.html')

# def refresh_id_token(refresh_token):
#     try:
#         refresh_url = f"https://securetoken.googleapis.com/v1/token?key={Config.FIREBASE_CONFIG['apiKey']}"
#         payload = {
#             'grant_type': 'refresh_token',
#             'refresh_token': refresh_token
#         }
#         response = requests.post(refresh_url, data=payload)
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as e:
#         print(f"Error refreshing ID token: {e}")
#         return None

# @bp.route('/check-verification')
# def check_verification():
#     if 'user_id_token' not in session or 'user_type' not in session:
#         return redirect(url_for('auth.signin'))

#     print("Session Data: ", session.get('user_data'))  # Add this line to debug

#     try:
#         id_token = session['user_id_token']
#         user_type = session['user_type']
#         local_id = session['local_id']
#         user_data = session['user_data']

#         # Attempt to get account info, refresh token if necessary
#         try:
#             account_info = firebase.auth().get_account_info(id_token)
#         except Exception as e:
#             if 'TOKEN_EXPIRED' in str(e):
#                 refresh_token = session.get('refresh_token')
#                 if refresh_token:
#                     new_tokens = refresh_id_token(refresh_token)
#                     if new_tokens:
#                         id_token = new_tokens['id_token']
#                         session['user_id_token'] = id_token
#                         account_info = firebase.auth().get_account_info(id_token)
#                     else:
#                         flash('Session expired, please log in again.', 'warning')
#                         return redirect(url_for('auth.signin'))
#                 else:
#                     flash('Session expired, please log in again.', 'warning')
#                     return redirect(url_for('auth.signin'))
#             else:
#                 raise e

#         email_verified = account_info['users'][0]['emailVerified']

#         if email_verified:
#             if user_type == 'doctor':
#                 # Create special email address for doctors
#                 name = user_data['full_name']
#                 special_email = generate_special_email(name)
#                 if special_email:
#                     # Update user's email in Firebase Authentication to the special email using Firebase Admin SDK
#                     auth.update_user(local_id, email=special_email)
                    
#                     # Store the special email in the Realtime Database
#                     firebase_db.child("special_emails").child(local_id).set({'special_email': special_email}, token=id_token)
                    
#                     # Send special email notification to the personal email
#                     personal_email = user_data['personal_email']
#                     send_special_email_notification(personal_email, special_email)
#                     flash('Please use your new email for future logins.', 'success')
#                 else:
#                     flash('Could not generate a valid special email.', 'danger')
#             return render_template('auth/check_verification.html')
#         else:
#             return render_template('auth/check_verification.html')
#     except Exception as e:
#         flash('An error occurred while checking email verification: ' + str(e), 'danger')
#         return render_template('auth/check_verification.html')


# @bp.route('/resend-verification-email', methods=['POST'])
# def resend_verification_email():
#     if 'user_id_token' not in session:
#         return {'status': 'error', 'message': 'User not logged in'}, 401

#     try:
#         id_token = session['user_id_token']
#         firebase.auth().send_email_verification(id_token)
#         return {'status': 'success', 'message': 'Verification email sent'}
#     except Exception as e:
#         return {'status': 'error', 'message': str(e)}, 400
=======
    
    
    
>>>>>>> R_Branch
