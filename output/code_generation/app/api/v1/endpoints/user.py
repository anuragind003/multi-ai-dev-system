from typing import List
from datetime import timedelta

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, get_current_active_user
from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException, ForbiddenException
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin
from app.schemas.common import MessageResponse
from app.services.user import UserService
from app.utils.logger import logger

router = APIRouter()

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Registers a new user with email and password. Email must be unique.",
    responses={
        status.HTTP_409_CONFLICT: {"model": MessageResponse, "description": "User with this email already exists"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": MessageResponse, "description": "Validation error"}
    }
)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint to create a new user.
    """
    user_service = UserService(db)
    try:
        user = await user_service.create_user(user_in)
        logger.info(f"API: User {user.email} created successfully.")
        return user
    except ConflictException as e:
        logger.warning(f"API: User creation failed due to conflict: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"API: Unexpected error during user creation: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get access token",
    description="Authenticates a user with email and password and returns a JWT access token.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": MessageResponse, "description": "Incorrect email or password"}
    }
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint for user login and JWT token generation.
    """
    user_service = UserService(db)
    try:
        user = await user_service.authenticate_user(form_data.username, form_data.password)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}, expires_delta=access_token_expires
        )
        logger.info(f"API: User {user.email} logged in successfully.")
        return {"access_token": access_token, "token_type": "bearer"}
    except UnauthorizedException as e:
        logger.warning(f"API: Login failed for user {form_data.username}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"API: Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description="Retrieves the details of the currently authenticated user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": MessageResponse, "description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"model": MessageResponse, "description": "Inactive user"}
    }
)
async def read_users_me(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Endpoint to get the current authenticated user's details.
    """
    logger.info(f"API: User {current_user.email} requested their own profile.")
    return current_user


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="Get all users (Admin only)",
    description="Retrieves a list of all registered users. Requires administrative privileges.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": MessageResponse, "description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"model": MessageResponse, "description": "Permission denied"}
    }
)
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user) # Placeholder for admin check
):
    """
    Endpoint to get a list of all users.
    NOTE: In a real application, this would require an 'admin' role check.
    For this example, any active authenticated user can access it.
    """
    # Example of a simple admin check (assuming user ID 1 is admin)
    # if current_user.id != 1:
    #     logger.warning(f"API: User {current_user.email} attempted to access all users without admin rights.")
    #     raise ForbiddenException(detail="Only administrators can view all users")

    user_service = UserService(db)
    users = await user_service.get_users(skip=skip, limit=limit)
    logger.info(f"API: User {current_user.email} retrieved {len(users)} users.")
    return users