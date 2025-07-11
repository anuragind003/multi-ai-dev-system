from typing import AsyncGenerator, List

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security import oauth2_scheme, decode_access_token, require_role
from schemas import TokenData
from models import UserRole
from utils.exceptions import UnauthorizedException, ForbiddenException
from crud import CRUDUser
from utils.logger import logger

async def get_current_user_token_data(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Dependency to get the decoded token data for the current authenticated user.
    Raises UnauthorizedException if the token is invalid or missing.
    """
    return decode_access_token(token)

async def get_current_active_user(
    token_data: TokenData = Depends(get_current_user_token_data),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency to get the current active user object from the database.
    Raises UnauthorizedException if the user is not found or inactive.
    """
    user_crud = CRUDUser()
    user = await user_crud.get_by_username(db, username=token_data.username)
    if not user:
        logger.warning(f"Authentication failed: User '{token_data.username}' not found.")
        raise UnauthorizedException(message="User not found.")
    if not user.is_active:
        logger.warning(f"Authentication failed: User '{token_data.username}' is inactive.")
        raise UnauthorizedException(message="Inactive user.")
    return user

# Specific role dependencies for convenience
def get_admin_user(current_user=Depends(require_role([UserRole.ADMIN]))):
    """Dependency for admin users."""
    return current_user

def get_auditor_or_admin_user(current_user=Depends(require_role([UserRole.AUDITOR, UserRole.ADMIN]))):
    """Dependency for auditor or admin users."""
    return current_user

def get_viewer_auditor_admin_user(current_user=Depends(require_role([UserRole.VIEWER, UserRole.AUDITOR, UserRole.ADMIN]))):
    """Dependency for any authenticated user."""
    return current_user