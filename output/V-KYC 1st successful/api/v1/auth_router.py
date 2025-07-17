import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import UserCreate, UserResponse, Token, HTTPError
from services.user_service import UserService
from core.security import create_access_token
from core.exceptions import UnauthorizedException, ConflictException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "Conflict: Username or email already registered"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new user in the system.
    - **username**: Unique username for the new user.
    - **email**: Unique email address for the new user.
    - **password**: Password for the new user (min 8 characters).
    - **role**: Optional role for the user (default: 'user').
    """
    user_service = UserService(db)
    try:
        new_user = await user_service.create_user(user_in)
        logger.info(f"User '{new_user.username}' successfully registered.")
        return new_user
    except ConflictException as e:
        logger.error(f"Registration failed: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during user registration: {e}")
        raise

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized: Invalid credentials"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user using username and password.
    Returns an access token upon successful authentication.
    - **username**: The user's username.
    - **password**: The user's password.
    """
    user_service = UserService(db)
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise UnauthorizedException(detail="Incorrect username or password")

    # You can customize token expiration here
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    logger.info(f"User '{user.username}' successfully logged in and received token.")
    return {"access_token": access_token, "token_type": "bearer"}