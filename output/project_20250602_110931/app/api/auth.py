from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from http import HTTPStatus
from app.models import User
from app.extensions import db
import logging

# Configure logging (basic setup for demonstration purposes)
# In a production application, logging would typically be configured globally
# in app.py or a dedicated configuration file.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Constants for validation
MIN_PASSWORD_LENGTH = 8

def _get_json_data():
    """
    Helper function to extract JSON data from the request.
    Returns the data, or an error response and status code if data is missing.
    """
    data = request.get_json()
    if not data:
        logger.warning("Request received without JSON data.")
        return None, jsonify({"message": "Request must contain JSON data"}), HTTPStatus.BAD_REQUEST
    return data, None, None

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registers a new user account.
    Expects 'email' and 'password' in the request JSON body.
    - Hashes the password before storing it.
    - Checks if a user with the given email already exists.
    """
    data, error_response, status_code = _get_json_data()
    if error_response:
        return error_response, status_code

    email = data.get('email')
    password = data.get('password')

    # Basic input validation for email and password presence
    if not email or not password:
        logger.warning("Registration attempt with missing email or password.")
        return jsonify({"message": "Email and password are required"}), HTTPStatus.BAD_REQUEST

    # Enforce a minimum password length for security
    if len(password) < MIN_PASSWORD_LENGTH:
        logger.warning(f"Registration attempt with password shorter than {MIN_PASSWORD_LENGTH} characters.")
        return jsonify({"message": f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"}), HTTPStatus.BAD_REQUEST

    try:
        # Check if a user with the provided email already exists in the database
        if User.query.filter_by(email=email).first():
            logger.info(f"Registration attempt for existing email: {email}")
            return jsonify({"message": "User with this email already exists"}), HTTPStatus.CONFLICT

        # Hash the password securely using Werkzeug's security functions
        hashed_password = generate_password_hash(password)

        # Create a new User instance with the provided email and hashed password
        new_user = User(email=email, password_hash=hashed_password)

        # Add the new user to the database session and commit the transaction
        db.session.add(new_user)
        db.session.commit()

        logger.info(f"User registered successfully: {email}")
        return jsonify({"message": "User registered successfully"}), HTTPStatus.CREATED

    except Exception as e:
        # Rollback the session in case of any database error to maintain data integrity
        db.session.rollback()
        # Log the error for debugging purposes with traceback information
        logger.error(f"Error during user registration for email {email}: {e}", exc_info=True)
        return jsonify({"message": "An internal server error occurred during registration"}), HTTPStatus.INTERNAL_SERVER_ERROR

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Logs in an existing user and issues a JWT access token.
    Expects 'email' and 'password' in the request JSON body.
    - Verifies the provided password against the stored hashed password.
    - If credentials are valid, creates and returns an access token.
    """
    data, error_response, status_code = _get_json_data()
    if error_response:
        return error_response, status_code

    email = data.get('email')
    password = data.get('password')

    # Basic input validation for email and password presence
    if not email or not password:
        logger.warning("Login attempt with missing email or password.")
        return jsonify({"message": "Email and password are required"}), HTTPStatus.BAD_REQUEST

    try:
        # Retrieve the user from the database by email
        user = User.query.filter_by(email=email).first()

        # Check if the user exists and if the provided password matches the stored hashed password
        if user and check_password_hash(user.password_hash, password):
            # Create an access token. The identity of the token will be the user's ID.
            # This ID can later be retrieved using get_jwt_identity() for authenticated requests.
            access_token = create_access_token(identity=user.id)
            logger.info(f"User logged in successfully: {email}")
            return jsonify(access_token=access_token), HTTPStatus.OK
        else:
            # Return unauthorized if credentials do not match.
            # Use a generic message to prevent enumeration attacks.
            logger.warning(f"Failed login attempt for email: {email} (Invalid credentials).")
            return jsonify({"message": "Invalid email or password"}), HTTPStatus.UNAUTHORIZED

    except Exception as e:
        # Log the error for debugging purposes with traceback information
        logger.error(f"Error during user login for email {email}: {e}", exc_info=True)
        return jsonify({"message": "An internal server error occurred during login"}), HTTPStatus.INTERNAL_SERVER_ERROR

@auth_bp.route('/logout', methods=['POST'])
@jwt_required() # This decorator ensures that a valid JWT is present in the request
def logout():
    """
    Logs out the current user.
    For stateless JWTs, this typically means instructing the client to discard the token.
    A server-side token blocklist could be implemented here for more robust invalidation,
    but for this simple application, it primarily serves as a confirmation endpoint.
    """
    current_user_id = get_jwt_identity()
    logger.info(f"User {current_user_id} has initiated logout.")

    # In a stateless JWT system, the client is responsible for discarding the token.
    # This endpoint simply confirms the logout action from the server's perspective.
    return jsonify({"message": "Successfully logged out"}), HTTPStatus.OK