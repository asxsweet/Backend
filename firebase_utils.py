import firebase_admin
from firebase_admin import credentials, firestore, storage, auth as admin_auth
import pyrebase
import os

# Import your Firebase configuration from config.py
from config import firebaseConfig, FIREBASE_ADMIN_CREDENTIALS_PATH

# Firebase Pyrebase initialization
# This is used for client-side authentication (signup, login)
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()  # Pyrebase authentication instance

# Firebase Admin SDK initialization
# This is used for server-side operations (verifying tokens, Firestore, Storage)
try:
    cred = credentials.Certificate(FIREBASE_ADMIN_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred, {
        'storageBucket': firebaseConfig['storageBucket']
    })
    db = firestore.client()  # Firestore client instance
    bucket = storage.bucket()  # Firebase Storage bucket instance
    admin_auth_sdk = admin_auth  # Admin Auth SDK for token verification
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    # Handle the error appropriately, perhaps by exiting or logging
    # For now, we'll just print and continue, but in a production app, you'd want more robust error handling.
    db = None
    bucket = None
    admin_auth_sdk = None

# Ensure a temporary directory exists for uploads
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)