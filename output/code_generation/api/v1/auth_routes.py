from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from models import Token, UserCreate, UserResponse, UserRole
from services.user_service import UserService
from security import verify_password, create_access_token, get_current_user, has_role
from database import get_db_session
from exceptions import UnauthorizedException, ConflictException
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_db_session),
    current_user: models.DBUser = Depends(has_role([UserRole.ADMIN])) # Only admin can register new users
):
    """
    Registers a new user. Only users with 'admin' role can perform this action.
    """
    user_service = UserService(db)
    existing_user = user_service.get_user_by_username(user_create.username)
    if existing_user:
        raise ConflictException(detail="Username already registered")
    
    try:
        db_user = user_service.create_user(user_create)
        return UserResponse.model_validate(db_user)
    except Exception as e:
        logger.error(f"Failed to register user {user_create.username}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session)
):
    """
    Authenticates a user and returns an access token.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise UnauthorizedException(detail="Incorrect username or password")
    
    if not user.is_active:
        logger.warning(f"Inactive user '{form_data.username}' attempted to log in.")
        raise UnauthorizedException(detail="User is inactive")

    # Include roles in the token payload
    access_token_data = {"sub": user.username, "roles": [user.role.value]}
    access_token = create_access_token(data=access_token_data)
    logger.info(f"User '{user.username}' successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: models.DBUser = Depends(get_current_user)
):
    """
    Retrieves information about the current authenticated user.
    Requires authentication.
    """
    return UserResponse.model_validate(current_user)