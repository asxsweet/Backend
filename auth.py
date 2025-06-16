from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime

# Import initialized Firebase instances from firebase_utils
from firebase_utils import auth, db, admin_auth_sdk

# Create a Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)


def token_required(f):
    """
    Decorator to protect routes, ensuring a valid Firebase ID token is provided.
    The UID from the token is stored in `request.uid`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Look for the token in the "Authorization" header
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]

        if not token:
            return jsonify({'message': 'Токен берілмеген'}), 401

        try:
            # Verify the token using Firebase Admin SDK
            decoded_token = admin_auth_sdk.verify_id_token(token)
            request.uid = decoded_token['uid']  # Store UID in request context
        except Exception as e:
            return jsonify({'message': 'Токен жарамсыз', 'error': str(e)}), 401

        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    Handles user registration. Creates a user in Firebase Authentication
    and stores user details in Firestore.
    """
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')

    if not email or not password:
        return jsonify({"error": "Электрондық пошта мен құпия сөз қажет"}), 400

    try:
        # Create user with email and password using Pyrebase
        user = auth.create_user_with_email_and_password(email, password)
        uid = user['localId']

        # Store user details in Firestore
        db.collection('users').document(uid).set({
            'email': email,
            'name': name,
            'created_at': datetime.utcnow()
        })
        return jsonify({"msg": "Тіркелу сәтті өтті"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Handles user login. Authenticates user with Firebase and returns an ID token.
    Updates last login time in Firestore.
    """
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Электрондық пошта мен құпия сөз қажет"}), 400

    try:
        # Sign in user with email and password using Pyrebase
        user = auth.sign_in_with_email_and_password(email, password)
        token = user['idToken']
        uid = user['localId']

        # Update last login time in Firestore
        db.collection('users').document(uid).update({
            'last_login': datetime.utcnow()
        })

        return jsonify({
            "msg": "Кіру сәтті өтті",
            "idToken": token,
            "uid": uid
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route('/protected', methods=['GET'])
@token_required
def protected():
    """
    Example of a protected route that requires a valid token.
    """
    return jsonify({
        'message': 'Бұл қорғалған маршрут',
        'uid': request.uid
    }), 200