from fastapi import APIRouter, Depends, status, Body, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from schemas import Token, UserCreate, UserResponse
from services import auth_service
from database import get_db
from core.exceptions import ConflictException, CredentialException
from loguru import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Allows a new user to register with a username, email, and password. Default role is 'user'."
)
async def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new user in the system.
    - **username**: Unique username for the user.
    - **email**: Unique email address.
    - **password**: Secure password (min 8 characters).
    - **role**: Optional, defaults to 'user'.
    """
    logger.info(f"Attempting to register new user: {user_in.username}")
    try:
        user = auth_service.register_user(db, user_in)
        return user
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Error during user registration for {user_in.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during registration.")

@router.post(
    "/token",
    response_model=Token,
    summary="Obtain JWT access token",
    description="Authenticates a user and returns a JWT access token for subsequent API calls. Uses OAuth2 password flow."
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates a user and returns a JWT token.
    - **username**: The user's username.
    - **password**: The user's password.
    """
    logger.info(f"Attempting to authenticate user: {form_data.username}")
    try:
        user = auth_service.authenticate_user(db, form_data.username, form_data.password)
        access_token = auth_service.create_user_access_token(user)
        return {"access_token": access_token, "token_type": "bearer"}
    except CredentialException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail, headers={"WWW-Authenticate": "Bearer"})
    except Exception as e:
        logger.error(f"Error during token generation for {form_data.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during token generation.")