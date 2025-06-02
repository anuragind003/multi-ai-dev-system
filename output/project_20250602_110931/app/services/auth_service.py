from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta, timezone
from flask import current_app
from app.models.user import User
from app.extensions import db
from typing import Optional, Tuple

class AuthService:
    """
    Encapsulates business logic for user authentication, including password hashing,
    JWT token generation, and user management.
    """

    @staticmethod
    def register_user(email: str, password: str) -> Optional[User]:
        """
        Registers a new user with the provided email and password.
        Hashes the password before storing it.

        Args:
            email (str): The user's email address.
            password (str): The user's plain-text password.

        Returns:
            User: The newly created User object if registration is successful.
            None: If a user with the email already exists or on a database error.
        """
        if not email or not password:
            current_app.logger.warning("Attempted user registration with empty email or password.")
            return None

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            current_app.logger.info(f"Registration failed: User with email {email} already exists.")
            return None

        try:
            # Hash the password for secure storage
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            new_user = User(email=email, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            current_app.logger.info(f"User {email} registered successfully.")
            return new_user
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error registering user {email}: {e}", exc_info=True)
            return None

    @staticmethod
    def authenticate_user(email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticates a user by verifying their email and password.
        If authentication is successful, generates a JWT token.

        Args:
            email (str): The user's email address.
            password (str): The user's plain-text password.

        Returns:
            tuple: A tuple containing (User object, JWT token) if authentication is successful.
            (None, None): Otherwise.
        """
        if not email or not password:
            current_app.logger.warning("Attempted user authentication with empty email or password.")
            return None, None

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            # Password matches, generate JWT token
            token = AuthService.generate_auth_token(user.id)
            if token:
                current_app.logger.info(f"User {email} authenticated successfully.")
                return user, token
            else:
                current_app.logger.error(f"Failed to generate token for user {email} after successful password check.")
                return None, None # Token generation failed
        current_app.logger.info(f"Authentication failed for user {email}: Invalid credentials.")
        return None, None

    @staticmethod
    def generate_auth_token(user_id: int) -> Optional[str]:
        """
        Generates a JSON Web Token (JWT) for the given user ID.

        The token includes:
        - 'user_id': The ID of the authenticated user.
        - 'exp': Expiration timestamp for the token.
        - 'iat': Issued at timestamp for the token.

        Args:
            user_id (int): The ID of the user for whom to generate the token.

        Returns:
            str: The encoded JWT token.
            None: If token generation fails (e.g., missing secret key).
        """
        try:
            # Get secret key and expiration days from Flask app configuration
            secret_key = current_app.config.get('SECRET_KEY')
            # Default to 7 days if not specified in config
            expiration_days = current_app.config.get('JWT_EXPIRATION_DAYS', 7)

            if not secret_key:
                current_app.logger.error("SECRET_KEY is not configured in Flask app, cannot generate JWT.")
                raise ValueError("SECRET_KEY is not configured in Flask app.")

            # Use timezone.utc for explicit UTC timestamps
            now = datetime.now(timezone.utc)
            payload = {
                'user_id': user_id,
                'exp': now + timedelta(days=expiration_days),
                'iat': now
            }
            # Encode the token using the application's secret key
            token = jwt.encode(payload, secret_key, algorithm='HS256')
            return token
        except Exception as e:
            current_app.logger.error(f"Error generating JWT token for user {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def verify_auth_token(token: str) -> Optional[int]:
        """
        Verifies a given JWT token and extracts the user ID if the token is valid.

        Args:
            token (str): The JWT token to verify.

        Returns:
            int: The user ID if the token is valid and not expired.
            None: If the token is invalid, expired, or on error.
        """
        try:
            secret_key = current_app.config.get('SECRET_KEY')
            if not secret_key:
                current_app.logger.error("SECRET_KEY is not configured in Flask app, cannot verify JWT.")
                raise ValueError("SECRET_KEY is not configured in Flask app.")

            # Decode the token. This will raise an exception if the token is invalid or expired.
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            if user_id is None:
                current_app.logger.warning("JWT payload missing 'user_id'.")
            return user_id
        except jwt.ExpiredSignatureError:
            current_app.logger.warning("JWT token has expired.")
            return None
        except jwt.InvalidTokenError:
            current_app.logger.warning("Invalid JWT token.")
            return None
        except Exception as e:
            current_app.logger.error(f"Error verifying JWT token: {e}", exc_info=True)
            return None

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID.

        Args:
            user_id (int): The ID of the user to retrieve.

        Returns:
            User: The User object if found.
            None: Otherwise.
        """
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Retrieves a user by their email address.

        Args:
            email (str): The email address of the user to retrieve.

        Returns:
            User: The User object if found.
            None: Otherwise.
        """
        return User.query.filter_by(email=email).first()

    @staticmethod
    def logout_user(token: str) -> bool:
        """
        Handles user logout. For stateless JWTs, this typically means
        informing the client to discard the token. If server-side invalidation
        (e.g., blacklisting) is implemented, this method would handle it.

        Args:
            token (str): The JWT token to be invalidated (if blacklisting is used).

        Returns:
            bool: True if logout logic was processed (e.g., token blacklisted),
                  False otherwise or if no server-side action is taken.
        """
        # In a typical stateless JWT setup, logout is client-side (discarding the token).
        # The commented-out code below shows how server-side blacklisting could be implemented.
        # For this project's current requirements (stateless JWTs), simply returning True
        # indicates that the client should proceed with discarding the token.
        #
        # Example of server-side blacklisting (requires a BlacklistedToken model):
        # from app.models.blacklisted_token import BlacklistedToken
        # try:
        #     # Decode token to get jti (JWT ID) if present, or just store the token itself
        #     # This requires 'jti' in your JWT payload generation
        #     # payload = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=['HS256'], options={"verify_signature": False})
        #     # jti = payload.get('jti')
        #     # if jti:
        #     #     # Ensure 'exp' is also in payload for expiration_time
        #     #     expiration_time = datetime.fromtimestamp(payload.get('exp'), tz=timezone.utc) if payload.get('exp') else datetime.now(timezone.utc) + timedelta(minutes=5) # Fallback
        #     #     blacklisted_token = BlacklistedToken(jti=jti, expiration_time=expiration_time)
        #     #     db.session.add(blacklisted_token)
        #     #     db.session.commit()
        #     #     current_app.logger.info(f"Token with jti {jti} blacklisted.")
        #     #     return True
        #     # else:
        #     #     current_app.logger.warning("JWT does not contain 'jti' for blacklisting. No server-side action taken.")
        #     #     return False
        # except Exception as e:
        #     current_app.logger.error(f"Error during logout/token blacklisting: {e}", exc_info=True)
        #     return False

        current_app.logger.info("Logout requested. Client should discard the JWT token.")
        return True