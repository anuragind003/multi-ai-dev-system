from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
import logging

from schemas import UserCreate, UserResponse, Token, LoginRequest, HTTPError
from services.auth_service import AuthService
from core.dependencies import get_auth_service
from core.exceptions import ConflictException, UnauthorizedException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "Conflict: Username or email already registered"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def register_user(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Registers a new user with the provided username, email, password, and role.
    The default role is 'qa_engineer'.
    """
    try:
        user = await auth_service.register_user(user_in)
        logger.info(f"User {user.username} registered successfully.")
        return user
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except Exception as e:
        logger.error(f"Error during user registration: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during registration.")

@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and get access token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized: Invalid credentials"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticates a user using username and password (OAuth2 form data).
    Returns an access token upon successful authentication.
    """
    login_data = LoginRequest(username=form_data.username, password=form_data.password)
    try:
        token = await auth_service.authenticate_user(login_data)
        logger.info(f"User {form_data.username} logged in successfully.")
        return token
    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error during user login for {form_data.username}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during login.")