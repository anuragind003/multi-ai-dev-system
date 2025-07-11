from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from services.user_service import UserService
from schemas import UserCreate, UserResponse, Token
from database import get_db
from auth import get_current_admin_user, get_current_active_user, verify_password, create_access_token, oauth2_scheme
from core.errors import ConflictError, NotFoundError, DatabaseError
from config import settings, logger
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/users", tags=["Users"])

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (Admin only)",
    dependencies=[Depends(get_current_admin_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new user with the specified username, password, role, and LAN ID.
    Only users with 'admin' role can access this endpoint.
    """
    user_service = UserService(db)
    try:
        new_user = user_service.create_user(user_data)
        return new_user
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    dependencies=[Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """
    Authenticates a user using username and password.
    Returns an access token upon successful authentication.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": [user.role.value]},
        expires_delta=access_token_expires
    )
    logger.info(f"User '{user.username}' logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user's details",
    dependencies=[Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def read_users_me(
    current_user: Annotated[UserResponse, Depends(get_current_active_user)]
):
    """
    Retrieves the details of the currently authenticated user.
    """
    return current_user

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (Admin only)",
    dependencies=[Depends(get_current_admin_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves a user's details by their ID.
    Only users with 'admin' role can access this endpoint.
    """
    user_service = UserService(db)
    try:
        user = user_service.get_user_by_id(user_id)
        return user
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List all users (Admin only)",
    dependencies=[Depends(get_current_admin_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieves a paginated list of all users.
    Only users with 'admin' role can access this endpoint.
    """
    user_service = UserService(db)
    users = user_service.get_all_users(skip=skip, limit=limit)
    return users

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user by ID (Admin only)",
    dependencies=[Depends(get_current_admin_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Deletes a user by their ID.
    Only users with 'admin' role can access this endpoint.
    """
    user_service = UserService(db)
    try:
        user_service.delete_user(user_id)
        return {"message": "User deleted successfully."}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))