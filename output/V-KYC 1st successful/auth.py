import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.config import settings
from app.schemas import TokenData, UserInDB, User
from app.exceptions import UnauthorizedException, ForbiddenException
from app.security import verify_password, create_access_token, decode_access_token

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer for token extraction from headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

# In-memory dummy user database for demonstration
# In a real application, this would be a database, LDAP, or an identity provider
DUMMY_USERS_DB = {
    settings.ADMIN_USERNAME: UserInDB(
        username=settings.ADMIN_USERNAME,
        hashed_password=verify_password(settings.ADMIN_PASSWORD, settings.ADMIN_PASSWORD), # Hash the default password
        roles=["admin", "tl", "process_manager"]
    ),
    "tl_user": UserInDB(
        username="tl_user",
        hashed_password=verify_password("tlpass", "tlpass"),
        roles=["tl"]
    ),
    "pm_user": UserInDB(
        username="pm_user",
        hashed_password=verify_password("pmpass", "pmpass"),
        roles=["process_manager"]
    ),
    "basic_user": UserInDB(
        username="basic_user",
        hashed_password=verify_password("basicpass", "basicpass"),
        roles=["basic_user"]
    )
}

async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Authenticates a user against the dummy database.
    """
    user = DUMMY_USERS_DB.get(username)
    if not user:
        logger.warning(f"Authentication failed: User '{username}' not found.")
        return None
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed: Invalid password for user '{username}'.")
        return None
    logger.info(f"User '{username}' authenticated successfully.")
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises UnauthorizedException if token is invalid or expired.
    """
    credentials_exception = UnauthorizedException(detail="Could not validate credentials")
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=roles)
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    
    user_in_db = DUMMY_USERS_DB.get(token_data.username)
    if user_in_db is None:
        raise credentials_exception
    
    logger.debug(f"Current user: {user_in_db.username}, Roles: {user_in_db.roles}")
    return User(username=user_in_db.username, roles=user_in_db.roles)

def has_role(required_roles: List[str]):
    """
    Dependency factory for role-based authorization.
    Checks if the current user has at least one of the required roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if not any(role in current_user.roles for role in required_roles):
            logger.warning(f"User '{current_user.username}' attempted to access forbidden resource. Required roles: {required_roles}, User roles: {current_user.roles}")
            raise ForbiddenException(detail="Not enough permissions")
        return current_user
    return role_checker

# Example usage of role_checker:
# @router.get("/admin_only", dependencies=[Depends(has_role(["admin"]))])
# async def admin_route():
#     return {"message": "Welcome, admin!"}