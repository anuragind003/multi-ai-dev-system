from typing import Annotated
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import UserCreate, UserLogin, UserResponse, Token
from services.user_service import UserService
from auth.dependencies import get_current_active_user, get_current_admin_user
from core.exceptions import UserAlreadyExistsException, UnauthorizedException
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users")

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Allows a new user to register with a username, password, and optional role. Only ADMIN can set roles other than AUDITOR."
)
async def register_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_active_user)] # Requires authentication to register
):
    """
    Registers a new user.
    - If `current_user` is ADMIN, they can set any role.
    - Otherwise, the role defaults to AUDITOR.
    """
    user_service = UserService(db)
    try:
        # Only admin can create users with roles other than AUDITOR
        if user_in.role != user_in.role.AUDITOR and current_user.role != current_user.role.ADMIN:
            logger.warning(f"User {current_user.username} (Role: {current_user.role}) attempted to create user with role {user_in.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create users with roles other than 'auditor'."
            )
        
        # If not admin, force role to AUDITOR
        if current_user.role != current_user.role.ADMIN:
            user_in.role = user_in.role.AUDITOR

        new_user = await user_service.create_user(user_in)
        logger.info(f"User {new_user.username} registered successfully by {current_user.username}.")
        return new_user
    except UserAlreadyExistsException as e:
        logger.warning(f"Registration failed: {e.detail}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)

@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticates a user and returns an access token."
)
async def login_for_access_token(
    user_in: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Authenticates a user and returns a JWT access token.
    """
    user_service = UserService(db)
    try:
        token = await user_service.authenticate_user(user_in.username, user_in.password)
        logger.info(f"User {user_in.username} logged in successfully.")
        return token
    except UnauthorizedException as e:
        logger.warning(f"Login failed for {user_in.username}: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieves the profile of the currently authenticated user."
)
async def read_users_me(
    current_user: Annotated[UserResponse, Depends(get_current_active_user)]
):
    """
    Retrieves the profile of the currently authenticated user.
    """
    return current_user

@router.get(
    "/all",
    response_model=List[UserResponse],
    summary="Get all users (Admin only)",
    description="Retrieves a list of all registered users. Requires ADMIN role."
)
async def read_all_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_admin_user)] # Admin role required
):
    """
    Retrieves all users. Accessible only by ADMIN users.
    """
    user_service = UserService(db)
    users = await user_service.get_all_users()
    logger.info(f"Admin user {current_user.username} fetched all users.")
    return users