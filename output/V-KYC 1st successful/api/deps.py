import logging
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_access_token
from core.exceptions import UnauthorizedException, ForbiddenException
from schemas.user_schema import TokenData
from services.user_service import UserService
from models.user_model import User # Import User model for type hinting

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer for handling token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency to get the current authenticated user.
    Validates the JWT token and fetches the user from the database.
    """
    credentials_exception = UnauthorizedException(
        message="Could not validate credentials. Please log in again."
    )
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Token payload missing 'sub' (email).")
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        logger.warning("Invalid JWT token.")
        raise credentials_exception
    except UnauthorizedException: # Re-raise if decode_access_token already raised it
        raise

    user_service = UserService(db)
    user = await user_service.get_user_by_email(token_data.email)
    if user is None:
        logger.warning(f"User '{token_data.email}' not found in DB after token validation.")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"User '{user.email}' is inactive.")
        raise UnauthorizedException(message="Inactive user.")
    
    logger.debug(f"Current user identified: {user.email}")
    return user

async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to ensure the current authenticated user is an administrator.
    """
    if not current_user.is_admin:
        logger.warning(f"User '{current_user.email}' attempted to access admin-only resource without admin privileges.")
        raise ForbiddenException(message="You do not have sufficient privileges to perform this action.")
    logger.debug(f"Admin user '{current_user.email}' authorized.")
    return current_user