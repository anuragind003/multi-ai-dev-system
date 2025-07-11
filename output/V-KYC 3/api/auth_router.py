from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from schemas import Token, UserCreate, UserResponse, MessageResponse
from services.user_service import UserService, get_user_service
from auth_utils import verify_password, create_access_token
from database import get_db
from core.exceptions import UnauthorizedException, ConflictException
from core.logging_config import setup_logging

logger = setup_logging()

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register_user(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Registers a new user in the system.
    - **email**: User's email address (must be unique).
    - **password**: User's password (min 8 characters).
    - **is_active**: Whether the user account is active (default: True).
    """
    logger.info(f"Attempting to register new user: {user_in.email}")
    db_user = user_service.create_user(user_in)
    logger.info(f"User registered successfully: {db_user.email}")
    return db_user

@router.post("/login", response_model=Token, summary="Authenticate user and get JWT token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticates a user with email and password and returns an access token.
    - **username**: User's email address.
    - **password**: User's password.
    """
    user = user_service.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise UnauthorizedException(detail="Incorrect email or password")
    
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {form_data.username}")
        raise UnauthorizedException(detail="User account is inactive")

    # Fetch user roles and permissions for token payload
    roles = [role.name for role in user.roles]
    permissions = []
    for role in user.roles:
        for perm in role.permissions:
            permissions.append(perm.name)
    
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email, "roles": roles, "permissions": list(set(permissions))}
    )
    logger.info(f"User {user.email} logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}