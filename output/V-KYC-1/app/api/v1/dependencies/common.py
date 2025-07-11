from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.core.database import get_db_session
from app.core.security import decode_access_token, check_admin_role
from app.core.exceptions import UnauthorizedException, ForbiddenException, NotFoundException
from app.models.models import User
from app.services.services import AuthService, RecordingService
from app.core.logging_config import logger

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises UnauthorizedException if the token is invalid or user not found.
    """
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT payload missing 'sub' (username).")
            raise UnauthorizedException("Invalid authentication token.")
    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error decoding token or extracting username: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    try:
        user = await auth_service.get_user_by_username(username)
        if user is None:
            logger.warning(f"User '{username}' from token not found in database.")
            raise UnauthorizedException("User not found.")
        logger.debug(f"Authenticated user: {user.username} with roles: {user.roles}")
        return user
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error fetching user '{username}' from database: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication."
        )

async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get the current authenticated user and ensure they have 'admin' role.
    Raises ForbiddenException if the user is not an admin.
    """
    try:
        check_admin_role(current_user.roles)
        logger.debug(f"Admin user {current_user.username} authenticated.")
        return current_user
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.detail,
        )
    except Exception as e:
        logger.error(f"Error checking admin role for user {current_user.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authorization."
        )

# Dependency for AuthService
async def get_auth_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> AuthService:
    """Provides an instance of AuthService with a database session."""
    return AuthService(db)

# Dependency for RecordingService
async def get_recording_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> RecordingService:
    """Provides an instance of RecordingService with a database session."""
    return RecordingService(db)