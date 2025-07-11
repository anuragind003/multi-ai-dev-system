from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import UserCreate, UserLogin, Token, UserResponse, ErrorResponse
from services import auth_service
from dependencies import get_db
from utils.exceptions import DuplicateEntryException, UnauthorizedException
from utils.logger import logger

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "User already exists"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def register_user(
    user_in: UserCreate = Body(..., description="User registration details"),
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new user with the provided username, password, and role.
    - **username**: Unique identifier for the user.
    - **password**: User's password (will be hashed).
    - **role**: User's role (e.g., 'viewer', 'auditor', 'admin').
    """
    try:
        new_user = await auth_service.register_user(db, user_in)
        return new_user
    except DuplicateEntryException as e:
        logger.warning(f"Registration failed: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during user registration: {e}")
        raise

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Invalid credentials"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def login_for_access_token(
    user_login: UserLogin = Body(..., description="User login credentials"),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user with username and password and returns an access token.
    - **username**: User's username.
    - **password**: User's password.
    """
    try:
        user = await auth_service.authenticate_user(db, user_login)
        access_token = await auth_service.create_access_token_for_user(user)
        return {"access_token": access_token, "token_type": "bearer"}
    except UnauthorizedException as e:
        logger.warning(f"Login failed: {e.message}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during token generation: {e}")
        raise