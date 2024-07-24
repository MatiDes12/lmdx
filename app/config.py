import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    REMEMBER_COOKIE_DURATION = 86400 * 30  # 30 days
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'PN@+qXZbPn1*$y%&!oiLfVMp'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///healthcare.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem'
    FIREBASE_CONFIG = json.loads(os.environ.get('FIREBASE_CONFIG', '{}'))
    UPLOAD_FOLDER = 'uploads/'
    MAX_CONTENT_LENGTH = 16 * 1000 * 1000  # 16 MB limit

    # Flask-Mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
