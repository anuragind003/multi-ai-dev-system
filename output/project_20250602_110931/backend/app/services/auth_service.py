from datetime import datetime, timedelta
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from app.models.user import User
from app.extensions import db

class AuthServiceError(Exception):
    """Base exception for authentication service errors."""
    pass

class UserAlreadyExistsError(AuthServiceError):
    """Raised when attempting to register a user with an email that already exists."""
    pass

class InvalidCredentialsError(AuthServiceError):
    """Raised when login credentials (email/password) are incorrect."""
    pass

class AuthService:
    """
    Encapsulates business logic related to user authentication,
    such as user registration, login validation, password hashing,
    and JWT token generation.
    """

    # Define a constant for JWT access token expiration time for better maintainability.
    ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    @staticmethod
    def _hash_password(password: str) -> str:
        """
        Hashes a plain-text password using Werkzeug's `generate_password_hash`.
        This method uses a strong, salted hash by default (e.g., pbkdf2:sha256),
        which is crucial for securely storing user passwords as per NFR4.3.1.
        """
        return generate_password_hash(password)

    @staticmethod
    def _check_password(hashed_password: str, password: str) -> bool:
        """
        Checks a plain-text password against a hashed password using Werkzeug's `check_password_hash`.
        This function handles the salt and hashing algorithm automatically.
        """
        return check_password_hash(hashed_password, password)

    @staticmethod
    def register_user(email: str, password: str) -> User:
        """
        Registers a new user with the provided email and password.

        Args:
            email: The user's email address. Must be unique.
            password: The user's plain-text password. It will be securely hashed before storage.

        Returns:
            The newly created User object.

        Raises:
            UserAlreadyExistsError: If a user with the given email already exists in the database.
        """
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            raise UserAlreadyExistsError("A user with this email already exists.")

        hashed_password = AuthService._hash_password(password)

        new_user = User(email=email, password_hash=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        return new_user

    @staticmethod
    def login_user(email: str, password: str) -> str:
        """
        Authenticates a user by verifying their email and password.
        Upon successful authentication, a JWT access token is generated,
        which can be used for subsequent authenticated requests.

        Args:
            email: The user's email address.
            password: The user's plain-text password.

        Returns:
            A JWT access token string.

        Raises:
            InvalidCredentialsError: If the email does not exist or the provided password
                                     does not match the stored hashed password.
        """
        user = User.query.filter_by(email=email).first()

        if not user or not AuthService._check_password(user.password_hash, password):
            raise InvalidCredentialsError("Invalid email or password.")

        access_token = create_access_token(identity=user.id, expires_delta=AuthService.ACCESS_TOKEN_EXPIRES)
        return access_token

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Retrieves a user object from the database by their unique ID.
        This method is commonly used by Flask-JWT-Extended's `user_lookup_loader`
        to load the user object associated with a JWT's identity when a protected
        endpoint is accessed.

        Args:
            user_id: The unique integer ID of the user.

        Returns:
            The User object if found, otherwise None.
        """
        return User.query.get(user_id)