import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
import json  # Import json module to parse the JSON string

# Load environment variables
load_dotenv()

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
    
    # Initialize Firestore client
    db = firestore.client()
    return db

# Initialize Firebase and Firestore
db = initialize_firebase()
