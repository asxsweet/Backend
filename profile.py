from flask import Blueprint, request, jsonify

# Import initialized Firebase instances and utility functions
from firebase_utils import db
from auth import token_required  # Import the decorator

# Create a Blueprint for profile-related routes
profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile/<uid>', methods=['GET'])
def get_profile(uid):
    """
    Retrieves user profile information for a given UID.
    """
    try:
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({'error': 'Қолданушы табылмады'}), 404

        user_data = user_doc.to_dict()

        return jsonify({
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            # Profile picture URL
            'photo_url': user_data.get('photo_url', None),
            'created_at': user_data.get('created_at').isoformat() if user_data.get('created_at') else None,
            'last_login': user_data.get('last_login').isoformat() if user_data.get('last_login') else None
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@profile_bp.route('/edit_profile', methods=['POST'])
@token_required
def edit_profile():
    """
    Allows an authenticated user to edit their own profile information.
    """
    try:
        uid = request.uid  # Get UID from the authenticated request
        data = request.json

        name = data.get('name')
        photo_url = data.get('photo_url')

        update_data = {}
        if name is not None:  # Only update if provided
            update_data['name'] = name
        if photo_url is not None:  # Only update if provided
            update_data['photo_url'] = photo_url

        if not update_data:
            return jsonify({'error': 'Өзгерту үшін деректер берілмеген'}), 400

        user_ref = db.collection('users').document(uid)
        user_ref.update(update_data)

        return jsonify({'msg': 'Профиль сәтті жаңартылды'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500 # type: ignore