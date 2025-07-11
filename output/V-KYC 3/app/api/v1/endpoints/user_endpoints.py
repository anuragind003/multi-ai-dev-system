from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserResponse, UserCreate, UserUpdate, Token, LoginRequest
from app.services.user_service import UserService
from app.security import authenticate_user, create_access_token
from app.auth import get_current_user, has_role, has_permission
from app.models import User
from app.exceptions import UnauthorizedException, NotFoundException, ConflictException, InvalidInputException
from app.logger import logger

router = APIRouter()

@router.post("/token", response_model=Token, summary="Authenticate User and Get JWT Token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticates a user with email and password and returns an access token.
    """
    user_service = UserService(db)
    user = authenticate_user(user_service, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise UnauthorizedException(detail="Incorrect username or password", message="Authentication Failed")
    
    access_token = create_access_token(data={"sub": user.email})
    logger.info(f"User {user.email} successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a New User")
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("user:write")) # Requires 'user:write' permission
):
    """
    Creates a new user account.
    Requires 'user:write' permission.
    """
    user_service = UserService(db)
    try:
        new_user = user_service.create_user(user)
        logger.info(f"User {current_user.email} created new user: {new_user.email}")
        return new_user
    except (ConflictException, NotFoundException, InvalidInputException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error creating user: {e}")
        raise InvalidInputException(detail="An unexpected error occurred during user creation.")

@router.get("/users/", response_model=List[UserResponse], summary="Get All Users")
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("user:read")) # Requires 'user:read' permission
):
    """
    Retrieves a list of all users with pagination.
    Requires 'user:read' permission.
    """
    user_service = UserService(db)
    users = user_service.get_all_users(skip=skip, limit=limit)
    return users

@router.get("/users/me", response_model=UserResponse, summary="Get Current Authenticated User")
async def read_users_me(
    current_user: User = Depends(get_current_user) # Only requires authentication
):
    """
    Retrieves details of the currently authenticated user.
    """
    return current_user

@router.get("/users/{user_id}", response_model=UserResponse, summary="Get User by ID")
async def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("user:read")) # Requires 'user:read' permission
):
    """
    Retrieves a single user by their ID.
    Requires 'user:read' permission.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    return user

@router.put("/users/{user_id}", response_model=UserResponse, summary="Update User Details")
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("user:write")) # Requires 'user:write' permission
):
    """
    Updates an existing user's details.
    Requires 'user:write' permission.
    """
    user_service = UserService(db)
    try:
        updated_user = user_service.update_user(user_id, user)
        logger.info(f"User {current_user.email} updated user: {updated_user.email} (ID: {user_id})")
        return updated_user
    except (NotFoundException, ConflictException, InvalidInputException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error updating user {user_id}: {e}")
        raise InvalidInputException(detail="An unexpected error occurred during user update.")

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a User")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("user:delete")) # Requires 'user:delete' permission
):
    """
    Deletes a user account.
    Requires 'user:delete' permission.
    """
    user_service = UserService(db)
    try:
        user_service.delete_user(user_id)
        logger.info(f"User {current_user.email} deleted user with ID: {user_id}")
        return {"message": "User deleted successfully"}
    except (NotFoundException, InvalidInputException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error deleting user {user_id}: {e}")
        raise InvalidInputException(detail="An unexpected error occurred during user deletion.")