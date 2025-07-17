import logging
from typing import Generator, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.core.security import verify_token
from app.services.user_service import UserService
from app.models.security_test import User, UserRole
from app.core.exceptions import UnauthorizedException, ForbiddenException

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
    db_session: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises UnauthorizedException if token is invalid or user not found.
    """
    try:
        payload = verify_token(token)
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None or user_id is None:
            raise UnauthorizedException(detail="Invalid token payload")
    except UnauthorizedException as e:
        logger.warning(f"Authentication failed: {e.detail}")
        raise UnauthorizedException(detail="Could not validate credentials")

    user_service = UserService(db_session)
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        logger.warning(f"User with ID {user_id} not found in DB after token validation.")
        raise UnauthorizedException(detail="User not found")
    
    logger.debug(f"User '{user.username}' (ID: {user.id}, Role: {user.role.value}) authenticated.")
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get the current active authenticated user.
    Raises ForbiddenException if user is inactive.
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user '{current_user.username}' attempted access.")
        raise ForbiddenException(detail="Inactive user")
    return current_user

def has_role(required_roles: List[UserRole]):
    """
    Dependency factory to check if the current user has one of the required roles.
    """
    async def _has_role(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
        if current_user.role not in required_roles:
            logger.warning(f"User '{current_user.username}' (Role: {current_user.role.value}) attempted access to resource requiring roles: {required_roles}.")
            raise ForbiddenException(detail="Not enough permissions")
        return current_user
    return _has_role