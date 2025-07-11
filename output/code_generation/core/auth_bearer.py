import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.exceptions import CredentialException, UserNotFoundException
from core.security import decode_access_token
from database import get_db
from schemas.user import TokenData
from services.user_service import UserService # Import the service

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Dependency to get the current authenticated user.
    Decodes the JWT token, fetches the user from the database,
    and ensures the user is active.
    """
    logger.debug(f"Attempting to authenticate token: {token[:10]}...") # Log first 10 chars
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise CredentialException(detail="Token payload missing email")
        token_data = TokenData(email=email)
    except CredentialException as e:
        logger.warning(f"Authentication failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error processing token data: {e}", exc_info=True)
        raise CredentialException(detail="Invalid token format")

    user_service = UserService(db)
    user = user_service.get_user_by_email(email=token_data.email)
    if user is None:
        logger.warning(f"Authentication failed: User '{token_data.email}' not found.")
        raise UserNotFoundException(detail="User not found")
    if not user.is_active:
        logger.warning(f"Authentication failed: User '{token_data.email}' is inactive.")
        raise CredentialException(detail="Inactive user")

    logger.info(f"User '{user.email}' authenticated successfully.")
    return user