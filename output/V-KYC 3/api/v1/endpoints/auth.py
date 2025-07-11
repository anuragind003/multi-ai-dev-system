import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from schemas import Token, LoginRequest, UserCreate, UserResponse
from services.user_service import UserService
from core.security import create_access_token, create_refresh_token
from core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/login", response_model=Token, summary="Authenticate User and Get JWT Tokens")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user using username and password.
    On successful authentication, returns an access token and a refresh token.
    """
    user_service = UserService(db)
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Login attempt failed for username: {form_data.username}")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
            code="INVALID_CREDENTIALS"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_superuser": user.is_superuser},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id, "is_superuser": user.is_superuser},
        expires_delta=refresh_token_expires
    )

    logger.info(f"User '{user.username}' logged in successfully.")
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_token_expires.total_seconds())
    )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a New User")
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new user in the system.
    Requires a unique username and email.
    """
    user_service = UserService(db)
    try:
        new_user = await user_service.create_user(user_data)
        logger.info(f"New user '{new_user.username}' registered successfully.")
        return new_user
    except CustomHTTPException as e:
        logger.error(f"User registration failed: {e.detail}")
        raise e # Re-raise custom exceptions
    except Exception as e:
        logger.critical(f"An unexpected error occurred during user registration: {e}", exc_info=True)
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration.",
            code="REGISTRATION_FAILED"
        )

@router.post("/refresh", response_model=Token, summary="Refresh Access Token using Refresh Token")
async def refresh_access_token(
    refresh_token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/refresh")), # Use refresh token as input
    db: AsyncSession = Depends(get_db)
):
    """
    Refreshes an expired access token using a valid refresh token.
    """
    from core.dependencies import get_current_user_from_token # Import here to avoid circular dependency

    # Use get_current_user_from_token to validate the refresh token
    # We pass `is_refresh_token=True` to ensure it's treated as a refresh token
    # and to allow it to be expired for access token purposes but valid for refresh.
    token_data = await get_current_user_from_token(refresh_token, db, is_refresh_token=True)

    # Ensure the token data contains necessary info for creating a new token
    if not token_data.username or token_data.user_id is None:
        logger.warning("Refresh token is missing essential user data.")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
            headers={"WWW-Authenticate": "Bearer"},
            code="INVALID_REFRESH_TOKEN_PAYLOAD"
        )

    # Create a new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": token_data.username, "user_id": token_data.user_id, "is_superuser": token_data.is_superuser},
        expires_delta=access_token_expires
    )

    logger.info(f"Access token refreshed for user ID: {token_data.user_id}")
    return Token(
        access_token=new_access_token,
        refresh_token=refresh_token, # Return the same refresh token, or generate a new one if desired
        expires_in=int(access_token_expires.total_seconds())
    )