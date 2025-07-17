from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from schemas import UserCreate, UserResponse, Token
from services import UserService
from auth import authenticate_user, create_access_token, get_current_active_user, has_role
from models import User, UserRole
from exceptions import UnauthorizedException, ConflictException
from logger import get_logger
from middleware import rate_limit_dependency

logger = get_logger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(rate_limit_dependency)] # Apply rate limiting to all user endpoints
)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user. Requires 'admin' role."
)
async def register_user(
    user_data: UserCreate,
    current_user: User = Depends(has_role([UserRole.ADMIN])), # Only admin can register new users
    db: Session = Depends(get_db)
):
    """
    Registers a new user with the provided details.
    """
    logger.info(f"Admin user {current_user.username} attempting to register new user: {user_data.username}",
                extra={"admin_user_id": current_user.id, "new_username": user_data.username})
    service = UserService(db)
    
    # Check if user already exists
    if service.get_user_by_username(user_data.username):
        raise ConflictException(f"User with username '{user_data.username}' already exists.")
    
    new_user = service.create_user(user_data)
    return new_user

@router.post(
    "/token",
    response_model=Token,
    summary="Get access token",
    description="Authenticates a user and returns an access token."
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates a user using username and password and returns a JWT access token.
    """
    logger.info(f"Attempting to authenticate user: {form_data.username}")
    service = UserService(db)
    user = authenticate_user(service, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Authentication failed for user: {form_data.username}")
        raise UnauthorizedException("Incorrect username or password.")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": [user.role.value]},
        expires_delta=access_token_expires
    )
    logger.info(f"User {user.username} successfully authenticated and received token.",
                extra={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Retrieves the details of the currently authenticated user."
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves the details of the currently authenticated user.
    """
    logger.info(f"User {current_user.username} requested own profile.",
                extra={"user_id": current_user.id})
    return current_user