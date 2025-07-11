from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from services.user_service import UserService
from services.auth_service import AuthService
from core.auth_bearer import JWTBearer
from core.exceptions import UnauthorizedException, InvalidCredentialsException
from schemas import TokenData
from core.security import verify_token
from models import User
from core.logger import logger

# Dependency for database session
DBSession = Annotated[Session, Depends(get_db)]

# Dependency for User Service
def get_user_service(db: DBSession) -> UserService:
    """Provides a User Service instance with a database session."""
    return UserService(db)

# Dependency for Auth Service
def get_auth_service(user_service: Annotated[UserService, Depends(get_user_service)]) -> AuthService:
    """Provides an Auth Service instance with a User Service dependency."""
    return AuthService(user_service)

# Dependency for current authenticated user
async def get_current_user(
    token: Annotated[str, Depends(JWTBearer())],
    user_service: Annotated[UserService, Depends(get_user_service)]
) -> User:
    """
    Authenticates and retrieves the current user based on the provided JWT token.
    Raises UnauthorizedException if the token is invalid or user not found.
    """
    try:
        payload = verify_token(token)
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token payload missing 'sub' (username).")
            raise InvalidCredentialsException(detail="Could not validate credentials: Token invalid.")
        token_data = TokenData(username=username)
    except InvalidCredentialsException as e:
        logger.warning(f"Invalid token credentials: {e.detail}")
        raise UnauthorizedException(detail=e.detail)
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise UnauthorizedException(detail="Could not validate credentials: Token processing error.")

    user = user_service.get_user_by_username(token_data.username)
    if user is None:
        logger.warning(f"User '{token_data.username}' not found for token.")
        raise UnauthorizedException(detail="Could not validate credentials: User not found.")
    
    if not user.is_active:
        logger.warning(f"User '{token_data.username}' is inactive.")
        raise UnauthorizedException(detail="Inactive user.")
    
    logger.info(f"User '{user.username}' authenticated successfully.")
    return user

# Dependency for current active superuser
async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Ensures the current authenticated user is an active superuser.
    Raises HTTPException if not authorized.
    """
    if not current_user.is_superuser:
        logger.warning(f"User '{current_user.username}' attempted superuser action without privileges.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user