import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List

from config import settings
from db.database import get_db
from db.models import User
from schemas.user import TokenData
from core.exceptions import UnauthorizedException, ForbiddenException
from auth.security import get_user_by_username # Import for user retrieval

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer for handling token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from a JWT token.
    Raises UnauthorizedException if token is invalid or user not found.
    """
    credentials_exception = UnauthorizedException("Could not validate credentials")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT payload missing 'sub' (username).")
            raise credentials_exception
        token_data = TokenData(username=username, roles=payload.get("roles", []))
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise credentials_exception
    
    user = get_user_by_username(db, token_data.username)
    if user is None:
        logger.warning(f"User '{token_data.username}' from token not found in database.")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"User '{user.username}' is inactive.")
        raise UnauthorizedException("Inactive user")
        
    logger.debug(f"User '{user.username}' authenticated successfully.")
    return user

def require_role(required_roles: List[str]):
    """
    Dependency factory to enforce role-based authorization.
    Usage: `Depends(require_role(["admin", "manager"]))`
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        user_roles = [current_user.role] # Assuming a single role for simplicity, can be extended to list of roles
        
        # Check if the user has any of the required roles
        if not any(role in required_roles for role in user_roles):
            logger.warning(f"User '{current_user.username}' with roles {user_roles} attempted to access resource requiring roles {required_roles}.")
            raise ForbiddenException("Not enough permissions")
        logger.debug(f"User '{current_user.username}' authorized with role '{current_user.role}'.")
        return current_user
    return role_checker