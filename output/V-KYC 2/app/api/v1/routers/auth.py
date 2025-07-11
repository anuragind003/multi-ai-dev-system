from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas import UserLogin, Token, UserResponse, UserCreate, HTTPError
from app.dependencies import get_db, get_current_active_user
from app.services.user_service import UserService
from app.security import create_access_token
from app.config import settings
from app.error_handling import CustomHTTPException
from app.models import User
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={status.HTTP_400_BAD_REQUEST: {"model": HTTPError},
               status.HTTP_401_UNAUTHORIZED: {"model": HTTPError}}
)

@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    description="Authenticates a user with username and password, returning a JWT access token upon success."
)
async def login_for_access_token(
    user_login: UserLogin,
    db: Session = Depends(get_db)
) -> Token:
    """
    Handles user login.
    - Validates username and password against the database.
    - If valid, generates a JWT access token.
    - Returns the access token and token type.
    """
    user_service = UserService(db)
    user = user_service.authenticate_user(user_login.username, user_login.password)
    
    if not user:
        logger.warning(f"Login attempt failed for user: {user_login.username} - Invalid credentials.")
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        logger.warning(f"Login attempt failed for user: {user_login.username} - Inactive account.")
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive account"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    logger.info(f"User '{user.username}' successfully logged in and received token.")
    return Token(access_token=access_token, token_type="bearer")

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user with a unique username and password. Returns the created user's details."
)
async def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Handles new user registration.
    - Validates input data (username, password, email).
    - Creates a new user in the database.
    - Returns the newly created user's public details.
    """
    user_service = UserService(db)
    try:
        new_user = user_service.create_user(user_create)
        logger.info(f"New user '{new_user.username}' registered successfully.")
        return UserResponse.model_validate(new_user)
    except CustomHTTPException as e:
        logger.warning(f"User registration failed for '{user_create.username}': {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred during user registration for '{user_create.username}': {e}")
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user due to an internal error."
        )

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description="Retrieves the details of the currently authenticated user.",
    responses={status.HTTP_401_UNAUTHORIZED: {"model": HTTPError}}
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Returns the details of the currently authenticated user.
    Requires a valid JWT token in the Authorization header.
    """
    logger.debug(f"Fetching details for current user: {current_user.username}")
    return UserResponse.model_validate(current_user)