from flask import Flask, jsonify
from auth import auth_bp
from posts import posts_bp
from profile import profile_bp

# Initialize Flask app
app = Flask(__name__)

# Register blueprints for modularity
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(posts_bp, url_prefix='/posts')
app.register_blueprint(profile_bp, url_prefix='/profile')

# --- Global Error Handlers ---
# These handlers catch exceptions raised by the application and return JSON responses.


@app.errorhandler(400)
def bad_request(e):
    """Handles Bad Request (400) errors."""
    return jsonify({'error': 'Қате сұраныс'}), 400


@app.errorhandler(401)
def unauthorized(e):
    """Handles Unauthorized (401) errors."""
    return jsonify({'error': 'Авторизация қажет'}), 401


@app.errorhandler(403)
def forbidden(e):
    """Handles Forbidden (403) errors."""
    return jsonify({'error': 'Рұқсат жоқ'}), 403


@app.errorhandler(404)
def not_found(e):
    """Handles Not Found (404) errors."""
    return jsonify({'error': 'Бет табылмады'}), 404


@app.errorhandler(500)
def server_error(e):
    """Handles Internal Server Error (500) errors."""
    # In a production environment, you might want to log the full exception details
    # but only return a generic message to the client for security.
    return jsonify({'error': 'Сервер қатесі'}), 500


if __name__ == '__main__':
    # Run the Flask app in debug mode.
    # Set debug=False for production environments.
    app.run(debug=True)