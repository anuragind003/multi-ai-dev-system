from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import UserCreate, UserResponse, UserLogin, Token, MessageResponse
from app.services import auth_service
from app.db import get_db
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user with email and password. Returns the created user's details.",
    responses={
        409: {"model": MessageResponse, "description": "Conflict - Email already registered"},
        422: {"model": MessageResponse, "description": "Validation Error"}
    }
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles user registration.
    - **user_in**: User details for registration (email, password).
    """
    logger.info(f"Attempting to register user: {user_in.email}")
    user = await auth_service.register_user(db, user_in)
    logger.info(f"User {user.email} registered successfully.")
    return user

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    description="Authenticates a user with email and password. Returns an access token on success.",
    responses={
        401: {"model": MessageResponse, "description": "Unauthorized - Invalid credentials"},
        422: {"model": MessageResponse, "description": "Validation Error"}
    }
)
async def login_for_access_token(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles user login and token generation.
    - **user_in**: User credentials (email, password).
    """
    logger.info(f"Attempting to authenticate user: {user_in.email}")
    user = await auth_service.authenticate_user(db, user_in)
    token = await auth_service.create_user_access_token(user)
    logger.info(f"User {user.email} successfully logged in.")
    return token