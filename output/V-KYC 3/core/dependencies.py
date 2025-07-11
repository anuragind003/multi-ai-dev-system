import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import TokenData
from services.user_service import UserService
from core.security import verify_token
from models import User
from core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer for extracting token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user_from_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    is_refresh_token: bool = False # Flag to indicate if it's a refresh token validation
) -> TokenData:
    """
    Decodes and validates a JWT token, then retrieves the user data from the payload.
    Raises CustomHTTPException if the token is invalid or user not found.
    """
    credentials_exception = CustomHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
        code="INVALID_CREDENTIALS"
    )
    try:
        payload = verify_token(token, is_refresh_token=is_refresh_token)
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        is_superuser: bool = payload.get("is_superuser", False)
        if username is None or user_id is None:
            logger.warning("Token payload missing username or user_id.")
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id, is_superuser=is_superuser)
    except CustomHTTPException as e:
        logger.warning(f"Token validation failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during token processing: {e}", exc_info=True)
        raise credentials_exception
    
    return token_data

async def get_current_user(
    token_data: Annotated[TokenData, Depends(get_current_user_from_token)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Retrieves the full User object from the database based on the token data.
    Raises CustomHTTPException if the user is not found.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(token_data.user_id)
    if user is None:
        logger.warning(f"User with ID {token_data.user_id} not found in DB, despite valid token.")
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            code="USER_NOT_FOUND"
        )
    logger.debug(f"Current user retrieved: {user.username}")
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Ensures the current user is active.
    Raises CustomHTTPException if the user is inactive.
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user '{current_user.username}' attempted to access resource.")
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
            code="INACTIVE_USER"
        )
    return current_user

async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Ensures the current user is an active superuser.
    Raises CustomHTTPException if the user is not a superuser.
    """
    if not current_user.is_superuser:
        logger.warning(f"User '{current_user.username}' (not superuser) attempted to access admin resource.")
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation forbidden: Requires superuser privileges",
            code="FORBIDDEN_ACCESS"
        )
    return current_user