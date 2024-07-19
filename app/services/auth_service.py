from app.models.user import User
from app import db

class AuthService:
    @staticmethod
    def signup(data):
        user = User(
            firebase_uid=data['firebase_uid'],
            name=data['name'],
            email=data['email']
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_user_by_firebase_uid(firebase_uid):
        return User.query.filter_by(firebase_uid=firebase_uid).first()
    
from firebase_admin import auth

def create_user(email, password):
    user = auth.create_user(email=email, password=password)
    return user

def verify_user(email, password):
    # Firebase Admin SDK does not support user login,
    # this part should be handled on the client side using Firebase SDK.
    pass
