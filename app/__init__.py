import firebase_admin
from firebase_admin import credentials, auth, firestore
import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
from flask_mail import Mail
from flask_bcrypt import Bcrypt  # Import Flask-Bcrypt
from .config import Config
from dotenv import load_dotenv
import os

# Initialize extensions
sqlalchemy_db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
bcrypt = Bcrypt()  # Initialize Bcrypt here

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Set secret key and other configurations
    app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')
    app.config['UPLOAD_FOLDER'] = 'uploads/'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000  # 16 MB limit

    # Initialize extensions
    sqlalchemy_db.init_app(app)
    migrate.init_app(app, sqlalchemy_db)
    Session(app)
    mail.init_app(app)
    bcrypt.init_app(app)  # Initialize Bcrypt with the app

    # Initialize Firebase Admin SDK
    initialize_firebase()

    # Import and register blueprints
    from .routes import auth, doctor, main, upload, patient, contact, admin
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.main_bp)
    app.register_blueprint(admin.bp, url_prefix='/admin')
    app.register_blueprint(doctor.bp, url_prefix='/doctor')
    app.register_blueprint(upload.bp, url_prefix='/upload')
    app.register_blueprint(patient.bp, url_prefix='/patient')
    app.register_blueprint(contact.bp, url_prefix='/contact')
    app.context_processor(inject_unread_messages_count)

    return app

def inject_unread_messages_count():
    from flask import session
    from .models_db import Message

    unread_messages_count = 0
    if 'user_id' in session and session.get('user_type') in ['patient', 'client', 'doctors']:
        user_id = session.get('user_id')
        unread_messages_count = Message.query.filter_by(recipient_id=user_id, is_read=False).count()
    return dict(unread_messages_count=unread_messages_count)

def initialize_firebase():
    # Retrieve JSON string from environment variable
    firebase_json = os.getenv('FIREBASE_ADMINSDK_JSON')
    if not firebase_json:
        raise ValueError("Missing or invalid FIREBASE_ADMINSDK_JSON in .env file")

    # Parse the JSON string into a Python dictionary
    try:
        firebase_credentials = json.loads(firebase_json)
    except json.JSONDecodeError as e:
        raise ValueError("Invalid JSON for FIREBASE_ADMINSDK_JSON: " + str(e))

    # Use the parsed credentials dictionary to initialize Firebase
    cred = credentials.Certificate(firebase_credentials)
    
    # Initialize the Firebase app only if it's not already initialized
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            'projectId': firebase_credentials.get('project_id', 'luminamedix')
        })
