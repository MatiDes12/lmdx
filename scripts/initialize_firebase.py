# initialize_firebase.py
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    # Path to your service account JSON file
    cred = credentials.Certificate('./app/config/firebase-adminsdk.json')
    
    # Explicitly set the Firebase project ID
    firebase_admin.initialize_app(cred, {
        'projectId': 'luminamedix'
    })
    
    # Initialize Firestore client
    db = firestore.client()
    return db

# Initialize Firebase and Firestore
db = initialize_firebase()