from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from datetime import timedelta
from schemas import UserCreate, UserResponse, Token, LoginRequest
from services import UserService
from dependencies import DBSession, get_current_user
from security import create_access_token
from exceptions import UnauthorizedException, ConflictException
from config import settings
import logging

logger = logging.getLogger("security_testing_api")

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a new user",
             description="Allows a new user to register with a username, email, and password. Default role is 'tester'.")
async def register_user(user_in: UserCreate, db: DBSession):
    user_service = UserService(db)
    try:
        new_user = await user_service.create_user(user_in)
        return new_user
    except ConflictException as e:
        logger.warning(f"Registration failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise

@router.post("/token", response_model=Token,
             summary="Obtain JWT token",
             description="Authenticates a user and returns an access token.")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession
):
    user_service = UserService(db)
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise UnauthorizedException(detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": [user.role.value]},
        expires_delta=access_token_expires
    )
    logger.info(f"User '{user.username}' logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse,
            summary="Get current user information",
            description="Retrieves details of the currently authenticated user.")
async def read_users_me(current_user: Annotated[UserResponse, Depends(get_current_user)]):
    return current_user