from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db as get_db_session
from app.core.security import (
    get_current_active_user as get_active_user_data,
    get_current_admin_user as get_admin_user_data,
    get_current_user as get_user_token_data,
    get_current_user_with_roles as get_user_with_roles_data,
)
from app.schemas import TokenData

# Re-exporting for cleaner imports in API endpoints
# This file acts as a central point for common dependencies

def get_db() -> Generator[Session, None, None]:
    """Dependency to get a database session."""
    yield from get_db_session()

def get_current_user(current_user_data: TokenData = Depends(get_user_token_data)) -> TokenData:
    """Dependency to get the current user's token data."""
    return current_user_data

def get_current_active_user(current_user_data: TokenData = Depends(get_active_user_data)) -> TokenData:
    """Dependency to get the current active user's token data."""
    return current_user_data

def get_current_admin_user(current_user_data: TokenData = Depends(get_admin_user_data)) -> TokenData:
    """Dependency to get the current active admin user's token data."""
    return current_user_data

def get_user_has_roles(required_roles: list) -> TokenData:
    """Dependency factory to check if the current user has any of the required roles."""
    return Depends(get_user_with_roles_data(required_roles))