from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated

from database import get_db
from schemas import LoginRequest, Token, UserCreate, UserResponse, HTTPError
from services.auth_service import AuthService
from services.user_service import UserService
from core.security import get_password_hash
from core.exceptions import UnauthorizedException, ConflictException, APIException
from utils.logger import setup_logging

logger = setup_logging()

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        status.HTTP_201_CREATED: {"model": UserResponse, "description": "User successfully registered"},
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "Email already registered"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation error"}
    }
)
async def register_user(
    user_create: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    user_service: Annotated[UserService, Depends(UserService)],
    auth_service: Annotated[AuthService, Depends(AuthService)]
):
    """
    Registers a new user with the provided email and password.
    The password will be hashed before storing.
    """
    logger.info(f"Attempting to register user with email: {user_create.email}")
    try:
        # Check if user already exists
        existing_user = user_service.get_user_by_email(db, user_create.email)
        if existing_user:
            logger.warning(f"Registration failed: Email '{user_create.email}' already registered.")
            raise ConflictException(detail="Email already registered")

        # Hash the password and create the user
        hashed_password = get_password_hash(user_create.password)
        new_user = auth_service.create_user(db, user_create.email, hashed_password)
        logger.info(f"User '{new_user.email}' registered successfully with ID: {new_user.id}")
        return new_user
    except APIException as e:
        raise e # Re-raise custom API exceptions
    except Exception as e:
        logger.exception(f"An unexpected error occurred during user registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration."
        )


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    responses={
        status.HTTP_200_OK: {"model": Token, "description": "Authentication successful, returns JWT token"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Invalid credentials"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation error"}
    }
)
async def login_for_access_token(
    form_data: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    auth_service: Annotated[AuthService, Depends(AuthService)]
):
    """
    Authenticates a user using their email and password.
    If successful, returns an access token (JWT).
    """
    logger.info(f"Attempting to log in user with email: {form_data.email}")
    try:
        user = auth_service.authenticate_user(db, form_data.email, form_data.password)
        if not user:
            logger.warning(f"Login failed for email: {form_data.email} - Invalid credentials.")
            raise UnauthorizedException(detail="Invalid credentials")

        access_token = auth_service.create_access_token(data={"sub": user.email})
        logger.info(f"User '{user.email}' logged in successfully. Token generated.")
        return Token(access_token=access_token, token_type="bearer")
    except APIException as e:
        raise e # Re-raise custom API exceptions
    except Exception as e:
        logger.exception(f"An unexpected error occurred during user login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login."
        )