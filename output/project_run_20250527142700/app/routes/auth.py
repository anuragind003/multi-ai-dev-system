from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import check_password_hash
from sqlalchemy.exc import SQLAlchemyError

# Assuming db is initialized in app/__init__.py or app.py
from app import db
# IMPORTANT: The User model is not defined in the provided database_schema.
# This code assumes a 'User' model exists in 'app.models' with at least
# 'id', 'username', and 'password_hash' fields for authentication purposes.
from app.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Handles user login.
    Accepts username and password, authenticates, and establishes a session.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400

    try:
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            # For MVP, a simple session-based login.
            # In a more robust system, this might involve JWTs or other token-based authentication.
            session['user_id'] = str(user.id) # Store user ID in session
            session['username'] = user.username
            current_app.logger.info(f"User '{username}' logged in successfully.")
            return jsonify({"status": "success", "message": "Logged in successfully", "username": user.username}), 200
        else:
            current_app.logger.warning(f"Failed login attempt for user: '{username}'")
            return jsonify({"status": "error", "message": "Invalid username or password"}), 401
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during login for '{username}': {e}")
        return jsonify({"status": "error", "message": "Internal server error during login"}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during login for '{username}': {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Handles user logout by clearing the session.
    """
    user_id = session.pop('user_id', None)
    username = session.pop('username', None)
    if user_id:
        current_app.logger.info(f"User '{username}' (ID: {user_id}) logged out.")
        return jsonify({"status": "success", "message": "Logged out successfully"}), 200
    else:
        current_app.logger.info("Logout attempt by unauthenticated user (no active session).")
        return jsonify({"status": "success", "message": "No active session to log out from"}), 200


@auth_bp.route('/status', methods=['GET'])
def status():
    """
    Checks the current authentication status of the user.
    """
    if 'user_id' in session:
        return jsonify({"status": "authenticated", "username": session.get('username')}), 200
    else:
        return jsonify({"status": "unauthenticated", "message": "No active session"}), 401