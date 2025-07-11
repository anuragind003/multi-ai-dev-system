from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from app.schemas import UserCreate, UserRead, UserLogin, Token, MessageResponse, HTTPError
from app.database import get_db
from app.services import UserService
from app.crud import CRUDUser, CRUDRole
from app.security import get_current_active_user, role_required
from app.models import User
from app.utils.logger import logger
from app.config import settings

router = APIRouter()

# Dependency for UserService
def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Provides a UserService instance with injected CRUD dependencies."""
    return UserService(CRUDUser(User), CRUDRole(Role))

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        status.HTTP_201_CREATED: {"model": UserRead, "description": "User successfully registered"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Invalid input or user already exists"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal server error"}
    }
)
async def register_user(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Registers a new user with the specified email, password, and role.
    The password will be hashed before storage.
    """
    logger.info(f"API: Registering user {user_create.email} with role {user_create.role_name}")
    new_user = await user_service.register_user(user_service.user_crud.db, user_create)
    return new_user

@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    responses={
        status.HTTP_200_OK: {"model": Token, "description": "Authentication successful, returns JWT token"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "User account is inactive"}
    }
)
async def login_for_access_token(
    user_login: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticates a user using email and password.
    Returns an access token upon successful authentication.
    """
    logger.info(f"API: Login attempt for user {user_login.email}")
    user = await user_service.authenticate_user(user_service.user_crud.db, user_login)
    access_token = await user_service.create_access_token_for_user(user)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current authenticated user's profile",
    responses={
        status.HTTP_200_OK: {"model": UserRead, "description": "Current user's profile"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "User account is inactive"}
    }
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieves the profile of the currently authenticated user.
    Requires a valid JWT token.
    """
    logger.info(f"API: Fetching profile for current user {current_user.email}")
    # The current_user object already contains the necessary data, but we can use service for consistency
    return await user_service.get_user_profile(user_service.user_crud.db, current_user.email)

@router.post(
    "/seed-initial-users",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed initial roles and users (Admin only)",
    responses={
        status.HTTP_200_OK: {"model": MessageResponse, "description": "Initial users and roles seeding initiated"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not authorized to perform this action"}
    }
)
async def seed_initial_users_endpoint(
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(role_required(["Admin"])) # Only Admin can trigger this
):
    """
    Triggers the seeding of initial roles (Admin, Team Lead, Process Manager) and their respective users.
    This endpoint is protected and only accessible by users with the 'Admin' role.
    It's primarily for initial setup or recovery, not for regular user creation.
    """
    logger.info(f"API: Admin user {current_user.email} triggered initial user seeding.")
    await user_service.seed_initial_users(user_service.user_crud.db)
    return MessageResponse(message="Initial users and roles seeding process initiated. Check logs for details.")