from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from schemas import TokenData, UserResponse
from models import User
from services.auth_service import AuthService
from services.user_service import UserService
from utils.exceptions import HTTPUnauthorized, HTTPForbidden
from utils.logger import get_logger

logger = get_logger(__name__)

# OAuth2PasswordBearer for handling token in Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(AuthService),
    user_service: UserService = Depends(UserService)
) -> UserResponse:
    """
    Dependency to get the current authenticated user from a JWT token.
    Raises HTTPUnauthorized if the token is invalid or user is not found/inactive.
    """
    try:
        token_data: TokenData = auth_service.decode_access_token(token)
    except HTTPUnauthorized as e:
        logger.warning(f"Authentication failed: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_data.username is None:
        logger.warning("Authentication failed: Token data missing username.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_service.get_user_by_username(db, token_data.username)
    if user is None:
        logger.warning(f"Authentication failed: User '{token_data.username}' not found in DB.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        logger.warning(f"Authentication failed: User '{user.username}' is inactive.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    logger.debug(f"Current user retrieved: {user.username}")
    return UserResponse.from_orm(user)

async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency to ensure the current user is active.
    (Redundant with get_current_user's check, but useful for clarity or if logic changes).
    """
    if not current_user.is_active:
        logger.warning(f"Access denied: User '{current_user.username}' is inactive.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: UserResponse = Depends(get_current_active_user)
) -> UserResponse:
    """
    Dependency to ensure the current user is an active administrator.
    """
    if not current_user.is_admin:
        logger.warning(f"Access denied: User '{current_user.username}' is not an admin.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation requires admin privileges")
    logger.debug(f"Admin user accessed: {current_user.username}")
    return current_user