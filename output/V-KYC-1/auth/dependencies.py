from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from database import get_db
from schemas import TokenData
from models import User, UserRole
from auth.security import verify_token
from core.exceptions import UnauthorizedException, ForbiddenException
from services.user_service import UserService
import logging

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer for handling token extraction from headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency to get the current user from the JWT token.
    Raises UnauthorizedException if the token is invalid or user not found.
    """
    credentials_exception = UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token)
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None or user_id is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id, roles=payload.get("roles", []))
    except JWTError:
        raise credentials_exception

    user_service = UserService(db)
    user = await user_service.get_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get the current active user.
    Raises UnauthorizedException if the user is inactive.
    """
    if not current_user.is_active:
        raise UnauthorizedException(detail="Inactive user")
    return current_user

def has_role(required_roles: list[UserRole]):
    """
    Dependency factory to check if the current user has any of the required roles.
    """
    async def role_checker(current_user: Annotated[User, Depends(get_current_active_user)]):
        if current_user.role not in required_roles:
            logger.warning(f"User {current_user.username} (Role: {current_user.role}) attempted to access resource requiring roles: {required_roles}")
            raise ForbiddenException(detail="Not enough permissions")
        return current_user
    return role_checker

# Specific role dependencies for convenience
get_current_admin_user = has_role([UserRole.ADMIN])
get_current_manager_or_admin_user = has_role([UserRole.MANAGER, UserRole.ADMIN])
get_current_auditor_or_higher_user = has_role([UserRole.AUDITOR, UserRole.MANAGER, UserRole.ADMIN])