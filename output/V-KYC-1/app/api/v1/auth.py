import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.core import security
from app.core.exceptions import ConflictException, UnauthorizedException
from app.dependencies import get_db, get_current_active_user
from app.models import User
from app.schemas import MessageResponse, Token, UserCreate, UserResponse, TokenData

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new user with the provided email and password.
    """
    db_user = crud.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise ConflictException(detail="Email already registered")

    hashed_password = security.get_password_hash(user_in.password)
    user = crud.create_user(db=db, user=user_in, hashed_password=hashed_password)
    logger.info(f"User {user.email} registered successfully.")
    return user

@router.post("/token", response_model=Token, summary="Obtain JWT access and refresh tokens")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates a user and returns JWT access and refresh tokens.
    """
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedException(detail="Incorrect email or password")
    if not user.is_active:
        raise UnauthorizedException(detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = security.create_access_token(
        data={"sub": user.email, "user_id": user.id, "roles": [user.role.value]},
        expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        data={"sub": user.email, "user_id": user.id, "roles": [user.role.value]},
        expires_delta=refresh_token_expires
    )
    logger.info(f"User {user.email} logged in successfully.")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "refresh_token": refresh_token
    }

@router.post("/token/refresh", response_model=Token, summary="Refresh JWT access token using refresh token")
async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refreshes an expired access token using a valid refresh token.
    """
    try:
        token_data = security.decode_token(refresh_token)
    except UnauthorizedException:
        raise UnauthorizedException(detail="Invalid or expired refresh token")

    user = crud.get_user_by_email(db, email=token_data.email)
    if not user or not user.is_active:
        raise UnauthorizedException(detail="User not found or inactive")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security.create_access_token(
        data={"sub": user.email, "user_id": user.id, "roles": [user.role.value]},
        expires_delta=access_token_expires
    )
    logger.info(f"Access token refreshed for user {user.email}.")
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "refresh_token": refresh_token # Return the same refresh token for now
    }

@router.get("/me", response_model=UserResponse, summary="Get current authenticated user's details")
async def read_users_me(
    current_user_data: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the details of the currently authenticated user.
    """
    user = crud.get_user(db, user_id=current_user_data.user_id)
    if not user:
        raise UnauthorizedException(detail="User not found")
    return user