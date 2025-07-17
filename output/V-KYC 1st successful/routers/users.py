from fastapi import APIRouter, Depends, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from database import get_db
from schemas import UserCreate, UserResponse, Token
from services import user_service
from auth import get_current_user, require_admin, revoke_token
from utils.errors import UnauthorizedException, ConflictException, NotFoundException
from utils.logger import logger
from config import get_settings

router = APIRouter(prefix="/users", tags=["Users"])
settings = get_settings()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Admin only)"
)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(require_admin) # Only admin can register new users
):
    """
    Registers a new user with the specified details.
    Requires 'admin' role.
    - **username**: Unique username.
    - **email**: Unique email address.
    - **password**: Strong password (min 8 chars, includes digit, upper, lower, special).
    - **full_name**: Optional full name.
    - **role**: User's role (e.g., 'team_lead', 'process_manager', 'admin').
    """
    logger.info(f"Admin user {current_user.username} attempting to register new user: {user_in.username}")
    try:
        new_user = await user_service.create_user(db, user_in)
        logger.info(f"User {new_user.username} registered successfully.")
        return new_user
    except ConflictException as e:
        logger.warning(f"User registration failed: {e.detail}")
        raise e

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token"
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user with username and password and returns an access token.
    - **username**: User's username.
    - **password**: User's password.
    """
    logger.info(f"Attempting login for user: {form_data.username}")
    user = await user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Authentication failed for user: {form_data.username}")
        raise UnauthorizedException(detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = user_service.create_access_token(
        data={"sub": user.username, "scopes": [user.role.value]},
        expires_delta=access_token_expires
    )
    logger.info(f"User {user.username} logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user's details"
)
async def read_users_me(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Retrieves the details of the currently authenticated user.
    """
    logger.info(f"Fetching details for current user: {current_user.username}")
    return current_user

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout current user by revoking token"
)
async def logout(
    response: Response,
    token: str = Depends(oauth2_scheme),
    current_user: UserResponse = Depends(get_current_user) # Ensure user is authenticated
):
    """
    Logs out the current user by blacklisting their access token.
    The token will be invalid for its remaining duration.
    """
    logger.info(f"User {current_user.username} attempting to logout.")
    # Calculate remaining expiry time for the token
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        expiration_timestamp = payload.get("exp")
        if expiration_timestamp:
            expires_at = datetime.fromtimestamp(expiration_timestamp)
            remaining_time = expires_at - datetime.utcnow()
            if remaining_time.total_seconds() > 0:
                await revoke_token(token, remaining_time)
                logger.info(f"Token for user {current_user.username} successfully blacklisted.")
            else:
                logger.warning(f"Token for user {current_user.username} already expired, no need to blacklist.")
        else:
            logger.warning(f"Token for user {current_user.username} has no expiration, cannot blacklist.")
    except JWTError as e:
        logger.error(f"Error decoding token during logout for user {current_user.username}: {e}")
        raise UnauthorizedException(detail="Invalid token provided for logout.")

    response.status_code = status.HTTP_204_NO_CONTENT
    return response