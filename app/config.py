import os

class Config:
    REMEMBER_COOKIE_DURATION = 86400 * 30  # 30 days
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'PN@+qXZbPn1*$y%&!oiLfVMp'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///healthcare.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem'
    FIREBASE_CONFIG = {
        "apiKey": "AIzaSyB52onJLQevCBAm710igMO_ulhnQh0-D1E",
        "authDomain": "luminamedix.firebaseapp.com",
        "databaseURL": "https://luminamedix-default-rtdb.firebaseio.com",
        "projectId": "luminamedix",
        "storageBucket": "luminamedix.appspot.com",
        "messagingSenderId": "156575457708",
        "appId": "1:156575457708:web:0eb4bab2af9f56be075a09",
        "measurementId": "G-1WGTMYMV1D"
    }
    UPLOAD_FOLDER = 'uploads/'
    MAX_CONTENT_LENGTH = 16 * 1000 * 1000  # 16 MB limit

    # Flask-Mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')