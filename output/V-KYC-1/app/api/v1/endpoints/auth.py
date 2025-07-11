from typing import Annotated
from fastapi import APIRouter, Depends, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.user_service import UserService
from app.dependencies import get_db, get_user_service, get_current_user
from app.core.security import create_access_token
from app.core.config import settings
from app.core.exceptions import DuplicateUserException, InvalidCredentialsException
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with a unique username and email.",
    responses={
        status.HTTP_201_CREATED: {"description": "User successfully registered"},
        status.HTTP_409_CONFLICT: {"description": "Username or email already exists"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
    }
)
async def register_user(
    user_data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Registers a new user.
    - **username**: Must be unique, alphanumeric.
    - **email**: Must be unique, valid email format.
    - **password**: Minimum 8 characters.
    """
    logger.info(f"Attempting to register user: {user_data.username}")
    try:
        new_user = await user_service.create_user(user_data)
        return new_user
    except DuplicateUserException as e:
        logger.warning(f"Registration failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during user registration: {e}", exc_info=True)
        raise status.HTTP_500_INTERNAL_SERVER_ERROR

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    description="Authenticates a user with username/email and password, returning an access token.",
    responses={
        status.HTTP_200_OK: {"description": "Authentication successful, token returned"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
    }
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Authenticates a user using OAuth2 password flow.
    - **username**: User's username or email.
    - **password**: User's password.
    """
    logger.info(f"Attempting to authenticate user: {form_data.username}")
    user_login_data = form_data.username # OAuth2PasswordRequestForm uses 'username' for identifier
    password = form_data.password

    try:
        # Use the service layer to authenticate
        authenticated_user = await user_service.authenticate_user(
            user_login=UserLogin(username_or_email=user_login_data, password=password)
        )
        
        access_token = create_access_token(
            data={"sub": authenticated_user.username}
        )
        logger.info(f"User '{authenticated_user.username}' successfully authenticated and token issued.")
        return {"access_token": access_token, "token_type": "bearer"}
    except InvalidCredentialsException as e:
        logger.warning(f"Authentication failed for {user_login_data}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during user login: {e}", exc_info=True)
        raise status.HTTP_500_INTERNAL_SERVER_ERROR

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description="Retrieves the details of the currently authenticated user.",
    responses={
        status.HTTP_200_OK: {"description": "Current user details retrieved"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_404_NOT_FOUND: {"description": "User not found"},
    }
)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves the details of the authenticated user.
    Requires a valid JWT token in the Authorization header.
    """
    logger.debug(f"Fetching details for current user: {current_user.username}")
    return current_user