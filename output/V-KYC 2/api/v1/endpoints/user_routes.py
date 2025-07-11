from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from services.user_service import UserService
from schemas import UserCreate, UserResponse, Token, LoginRequest
from security import create_access_token, get_current_user
from utils.logger import logger

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user with a specified role.
    """
    user_service = UserService(db)
    logger.info(f"Registering new user: {user_data.username} with role: {user_data.role.value}")
    new_user = user_service.create_user(user_data)
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates a user and returns an access token.
    Uses OAuth2PasswordRequestForm for username/password.
    """
    user_service = UserService(db)
    login_request = LoginRequest(username=form_data.username, password=form_data.password)
    user = user_service.authenticate_user(login_request)
    
    # Ensure user has a role before creating token
    if not user.role:
        logger.error(f"User {user.username} has no role assigned, cannot issue token.")
        # This should ideally not happen if user creation enforces roles
        # but as a safeguard, prevent token issuance.
        raise status.HTTP_500_INTERNAL_SERVER_ERROR # Or a more specific error
    
    access_token_expires = timedelta(minutes=30) # Use a specific expiry for tokens
    
    # Store role name (string value) in the token payload
    access_token = create_access_token(
        data={"sub": user.username, "roles": [user.role.name.value]},
        expires_delta=access_token_expires
    )
    logger.info(f"User {user.username} successfully logged in and received token.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Retrieves the current authenticated user's profile.
    Requires authentication.
    """
    logger.info(f"Fetching profile for user: {current_user.username}")
    return current_user