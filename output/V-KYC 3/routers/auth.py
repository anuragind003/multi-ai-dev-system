from datetime import timedelta
from fastapi import APIRouter, Depends, status, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from schemas import Token, UserResponse, ErrorResponse
from services import UserService
from middleware.security import get_user_service, create_access_token
from utils.exceptions import UnauthorizedException
from utils.logger import logger
from config import get_settings

settings = get_settings()

router = APIRouter(
    tags=["Authentication"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    description="Authenticates a user with username (email) and password, returning an access token.",
    responses={
        status.HTTP_200_OK: {"description": "Token successfully generated"},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid username or password"}
    }
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    """
    Endpoint for user login.
    - **username**: User's email address.
    - **password**: User's password.
    """
    logger.info(f"Login attempt for user: {form_data.username}")
    try:
        user_in_db = await user_service.user_repo.get_by_email(form_data.username)
        if not user_in_db or not user_service.verify_password(form_data.password, user_in_db.hashed_password):
            logger.warning(f"Failed login attempt for user: {form_data.username} (invalid credentials)")
            raise UnauthorizedException(detail="Incorrect username or password")
        
        if not user_in_db.is_active:
            logger.warning(f"Failed login attempt for user: {form_data.username} (inactive account)")
            raise UnauthorizedException(detail="Account is inactive")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_in_db.email, "scopes": ["me", "users:read", "users:write"] if user_in_db.is_admin else ["me"]},
            expires_delta=access_token_expires
        )
        logger.info(f"User {user_in_db.email} successfully logged in.")
        return Token(access_token=access_token, token_type="bearer", expires_in=int(access_token_expires.total_seconds()))
    except UnauthorizedException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during login for {form_data.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during authentication."
        )