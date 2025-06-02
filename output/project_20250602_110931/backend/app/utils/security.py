import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)
# Basic configuration for demonstration. In a real application, this would be configured centrally.
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Configuration ---
# It is crucial to load the secret key from environment variables
# for production deployments to ensure security. A default value
# is provided here for development purposes, but it MUST be replaced
# with a strong, randomly generated key in a production environment.
# IMPORTANT: For production, the application should ideally fail to start
# if SECRET_KEY is not properly configured.
SECRET_KEY = os.environ.get("SECRET_KEY", "your_super_secret_key_please_change_me_in_production")
ALGORITHM = "HS256"  # The algorithm used for signing the JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Access token validity period in minutes

# --- Password Hashing and Verification ---

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Bcrypt is a strong, adaptive hashing algorithm designed for passwords.
    It automatically handles salting, which protects against rainbow table attacks.

    Args:
        password (str): The plain-text password string to hash.

    Returns:
        str: The hashed password string, suitable for storage in a database.
    """
    # bcrypt.gensalt() generates a new, random salt for each hash.
    # This ensures that even if two users have the same password, their
    # hashed passwords will be different, preventing pre-computation attacks.
    # The default rounds (cost factor) for bcrypt.gensalt() is usually sufficient.
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hashed password.

    Args:
        plain_password (str): The plain-text password provided by the user (e.g., during login).
        hashed_password (str): The hashed password retrieved from the database.

    Returns:
        bool: True if the plain password matches the hashed password, False otherwise.
    """
    try:
        # bcrypt.checkpw handles the salting and hashing internally for comparison.
        # It returns True if the plain_password, when hashed with the salt embedded
        # in hashed_password, matches the hashed_password.
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # This exception can occur if the hashed_password is not a valid bcrypt hash
        # (e.g., it's corrupted, not a bcrypt hash at all, or has an invalid format).
        # In such cases, the password cannot be verified.
        logger.error("Stored hashed password format is invalid during verification.")
        return False
    except Exception as e:
        # Catch any other unexpected errors during verification.
        logger.error(f"An unexpected error occurred during password verification: {e}", exc_info=True)
        return False

# --- JWT Token Handling ---

def _check_secret_key_configured():
    """
    Helper function to ensure SECRET_KEY is not the default placeholder.
    Raises a ValueError if the key is insecure.
    """
    if not SECRET_KEY or SECRET_KEY == "your_super_secret_key_please_change_me_in_production":
        error_msg = ("SECRET_KEY is not set or is using the default value. "
                     "This is a critical security vulnerability. "
                     "Please set the 'SECRET_KEY' environment variable for production.")
        logger.critical(error_msg)
        raise ValueError(error_msg)

def generate_jwt_token(user_id: int) -> str:
    """
    Generates a JSON Web Token (JWT) for a given user ID.

    The token includes the user's ID as the subject ('sub') and an expiration
    timestamp ('exp') to ensure tokens are not valid indefinitely.

    Args:
        user_id (int): The unique identifier of the user for whom the token is generated.

    Returns:
        str: The encoded JWT token string.
    """
    _check_secret_key_configured()

    # Calculate the expiration time for the token.
    # Tokens are typically short-lived to reduce the window of opportunity
    # for token compromise. Use timezone-aware datetime.
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Define the payload (claims) for the JWT.
    # 'sub' (subject) is a standard JWT claim used to identify the principal (user).
    # 'exp' (expiration time) is another standard claim, indicating when the token expires.
    payload = {
        "sub": user_id,
        "exp": expire
    }

    # Encode the token using the specified payload, secret key, and algorithm.
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_jwt_token(token: str) -> Optional[int]:
    """
    Decodes a JWT token and returns the user ID if the token is valid and not expired.

    Handles common JWT errors such as expiration and invalid signatures.

    Args:
        token (str): The JWT token string to decode.

    Returns:
        Optional[int]: The user ID extracted from the token if valid, otherwise None.
    """
    _check_secret_key_configured()

    try:
        # Decode the token using the secret key and the expected algorithm.
        # The algorithms parameter is a list because a token might be signed
        # with one of several allowed algorithms.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract the user ID from the 'sub' claim in the payload.
        user_id = payload.get("sub")
        
        if user_id is None:
            # If the 'sub' claim is missing, the token is malformed for our use case.
            logger.warning("JWT Token payload is missing 'sub' claim.")
            return None
        
        return int(user_id)
    except jwt.ExpiredSignatureError:
        # This exception is raised if the 'exp' claim indicates the token has expired.
        logger.info("JWT Token has expired.") # Info level as this is a common, expected scenario
        return None
    except jwt.InvalidTokenError:
        # This is a general exception for various token invalidities,
        # such as an incorrect signature, malformed token structure, etc.
        logger.warning("Invalid JWT Token (e.g., wrong signature, malformed, or tampered).")
        return None
    except Exception as e:
        # Catch any other unexpected errors during the decoding process.
        logger.error(f"An unexpected error occurred during JWT decoding: {e}", exc_info=True)
        return None