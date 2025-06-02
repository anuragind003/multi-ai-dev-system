import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Configuration for JWT and password hashing
# It's good practice to load these from environment variables or a config file.
# WARNING: The default value provided here is for development/example purposes ONLY.
# In a real production application, ensure FLASK_SECRET_KEY is set to a strong,
# unique, and randomly generated secret value (e.g., using os.urandom(32).hex()).
# NEVER hardcode a weak or guessable secret in production.
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "a_very_insecure_default_secret_key_change_this_in_production_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Bcrypt is a strong hashing algorithm designed for passwords,
    which includes a salt and is computationally intensive to deter
    brute-force attacks.

    Args:
        password: The plain-text password string.

    Returns:
        The hashed password as a UTF-8 decoded string.
    """
    # bcrypt.gensalt() generates a new salt for each hash,
    # making rainbow table attacks ineffective.
    # The default rounds are usually sufficient, but can be specified: bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')

def check_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a bcrypt hashed password.

    Args:
        plain_password: The plain-text password string provided by the user.
        hashed_password: The stored bcrypt hashed password string.

    Returns:
        True if the plain password matches the hashed password, False otherwise.
    """
    try:
        # bcrypt.checkpw handles the salt extraction and hashing internally.
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # This can happen if the hashed_password is not a valid bcrypt hash
        # (e.g., wrong format, corrupted).
        return False

def _create_token(data: Dict[str, Any], expires_delta: Optional[timedelta], default_expire_value: int, unit: str) -> str:
    """
    Helper function to create a JWT token with common logic.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        if unit == "minutes":
            expire = now + timedelta(minutes=default_expire_value)
        elif unit == "days":
            expire = now + timedelta(days=default_expire_value)
        else:
            # This case should ideally not be reached with correct usage
            raise ValueError("Invalid unit for token expiration. Must be 'minutes' or 'days'.")

    to_encode.update({"exp": expire.timestamp(), "iat": now.timestamp()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.

    Args:
        data: A dictionary containing the payload for the token (e.g., user_id).
        expires_delta: Optional timedelta for token expiration. If None, uses
                       ACCESS_TOKEN_EXPIRE_MINUTES from configuration.

    Returns:
        The encoded JWT access token string.
    """
    return _create_token(data, expires_delta, ACCESS_TOKEN_EXPIRE_MINUTES, "minutes")

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT refresh token.

    Refresh tokens typically have a longer expiration time than access tokens
    and are used to obtain new access tokens without re-authenticating.

    Args:
        data: A dictionary containing the payload for the token (e.g., user_id).
        expires_delta: Optional timedelta for token expiration. If None, uses
                       REFRESH_TOKEN_EXPIRE_DAYS from configuration.

    Returns:
        The encoded JWT refresh token string.
    """
    return _create_token(data, expires_delta, REFRESH_TOKEN_EXPIRE_DAYS, "days")

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates a JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        A dictionary containing the token's payload if valid, None otherwise.
    """
    try:
        # jwt.decode verifies the signature and expiration time automatically.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.InvalidTokenError:
        # Token is invalid (e.g., wrong signature, malformed, or tampered)
        return None
    # Other exceptions (e.g., TypeError if token is not a string) are not caught
    # here, as they typically indicate a programming error or unexpected input
    # that should propagate or be handled by the caller.

# Example usage (for testing purposes, not part of the main application logic)
if __name__ == "__main__":
    print("--- Password Hashing and Checking ---")
    test_password = "mysecretpassword123"
    print(f"Original password: {test_password}")

    hashed_pw = hash_password(test_password)
    print(f"Hashed password: {hashed_pw}")

    # Test correct password
    if check_password(test_password, hashed_pw):
        print("Password check successful: Correct password matches.")
    else:
        print("Password check failed: Correct password does NOT match.")

    # Test incorrect password
    wrong_password = "wrongpassword"
    if check_password(wrong_password, hashed_pw):
        print("Password check failed: Incorrect password matches (ERROR!).")
    else:
        print("Password check successful: Incorrect password does NOT match.")

    # Test with an invalid hash
    invalid_hash = "not_a_valid_bcrypt_hash"
    if check_password(test_password, invalid_hash):
        print("Password check failed: Matched against invalid hash (ERROR!).")
    else:
        print("Password check successful: Did not match against invalid hash.")

    print("\n--- JWT Token Handling ---")
    user_id = 123
    user_email = "test@example.com"
    token_data = {"user_id": user_id, "email": user_email}

    # Create an access token
    access_token = create_access_token(token_data)
    print(f"Generated Access Token: {access_token}")

    # Decode the access token
    decoded_access_payload = decode_token(access_token)
    if decoded_access_payload:
        print(f"Decoded Access Token Payload: {decoded_access_payload}")
        assert decoded_access_payload.get("user_id") == user_id
        assert decoded_access_payload.get("email") == user_email
        print("Access token decoding successful.")
    else:
        print("Access token decoding failed.")

    # Create a refresh token
    refresh_token = create_refresh_token(token_data)
    print(f"Generated Refresh Token: {refresh_token}")

    # Decode the refresh token
    decoded_refresh_payload = decode_token(refresh_token)
    if decoded_refresh_payload:
        print(f"Decoded Refresh Token Payload: {decoded_refresh_payload}")
        assert decoded_refresh_payload.get("user_id") == user_id
        assert decoded_refresh_payload.get("email") == user_email
        print("Refresh token decoding successful.")
    else:
        print("Refresh token decoding failed.")

    # Test expired token (create a token that expires immediately)
    print("\n--- Testing Expired Token ---")
    expired_token = create_access_token(token_data, expires_delta=timedelta(seconds=-1))
    print(f"Generated Expired Token: {expired_token}")
    decoded_expired_payload = decode_token(expired_token)
    if decoded_expired_payload is None:
        print("Expired token correctly identified as None (expected).")
    else:
        print(f"Expired token incorrectly decoded: {decoded_expired_payload} (ERROR!).")

    # Test invalid token (e.g., tampered or wrong secret)
    print("\n--- Testing Invalid Token ---")
    tampered_token = access_token + "tamper" # Simple tampering
    decoded_tampered_payload = decode_token(tampered_token)
    if decoded_tampered_payload is None:
        print("Tampered token correctly identified as None (expected).")
    else:
        print(f"Tampered token incorrectly decoded: {decoded_tampered_payload} (ERROR!).")

    # Test with a token signed with a different secret (simulated)
    # This requires temporarily changing the SECRET_KEY for demonstration.
    # In a real test suite, use mocking or dependency injection.
    original_secret = SECRET_KEY
    global SECRET_KEY # Necessary to modify global in this scope
    SECRET_KEY = "another_secret_key_for_testing"
    token_from_other_secret = create_access_token(token_data)
    SECRET_KEY = original_secret # Revert to original secret

    decoded_other_secret_payload = decode_token(token_from_other_secret)
    if decoded_other_secret_payload is None:
        print("Token signed with different secret correctly identified as None (expected).")
    else:
        print(f"Token signed with different secret incorrectly decoded: {decoded_other_secret_payload} (ERROR!).")