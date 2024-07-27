from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
from flask_mail import Mail
from .config import Config
from dotenv import load_dotenv
import os
import firebase_admin
from firebase_admin import credentials

# Initialize extensions
sqlalchemy_db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

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

    # Import and register blueprints
    from .routes import auth, doctor, main, upload, patient, contact, admin
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.main_bp)
    app.register_blueprint(admin.bp, url_prefix='/admin')
    app.register_blueprint(doctor.bp, url_prefix='/doctor')
    app.register_blueprint(upload.bp, url_prefix='/upload')
    app.register_blueprint(patient.bp, url_prefix='/patient')
    app.register_blueprint(contact.bp, url_prefix='/contact')
    
    return app
