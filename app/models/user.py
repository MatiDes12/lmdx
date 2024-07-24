# from flask_login import UserMixin
# import pyrebase
# from ..config import Config

# firebase = pyrebase.initialize_app(Config.FIREBASE_CONFIG)
# auth = firebase.auth()
# db = firebase.database()

# class User(UserMixin):
#     def __init__(self, uid, email):
#         self.id = uid
#         self.email = email

#     @staticmethod
#     def get(user_id):
#         user = db.child("users").child(user_id).get().val()
#         if user:
#             return User(user_id, user['email'])
#         return None

# from app import db
# from flask_login import UserMixin

# class User(UserMixin, db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     firebase_uid = db.Column(db.String(128), unique=True, nullable=False)
#     name = db.Column(db.String(64), nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)

# from app import sqlalchemy_db as db
# from flask_login import UserMixin

# class User(UserMixin, db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     firebase_uid = db.Column(db.String(128), unique=True, nullable=False)
#     name = db.Column(db.String(64), nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     password = db.Column(db.String(128), nullable=False)  # Ensure you have a password field
#     theme = db.Column(db.String(20), default='light')  # Example of additional fields
#     language = db.Column(db.String(20), default='en')
#     timezone = db.Column(db.String(20), default='UTC')