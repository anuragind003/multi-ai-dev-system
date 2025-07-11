from fastapi import APIRouter, Depends, status, HTTPException, Body
from typing import List, Optional
import logging

from schemas.user import UserCreate, UserUpdate, UserResponse, Token
from services.user_service import UserService
from utils.dependencies import get_user_service
from security.auth import authenticate_user_dependency, create_access_token, get_current_active_user, get_current_active_superuser
from exceptions import NotFoundException, ConflictException, UnauthorizedException, ForbiddenException, InvalidInputException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/token", response_model=Token, summary="Authenticate User and Get JWT Token")
async def login_for_access_token(
    user_service: UserService = Depends(get_user_service),
    email: str = Body(..., embed=True, example="user@example.com"),
    password: str = Body(..., embed=True, example="password123")
):
    """
    Authenticates a user with email and password and returns an access token.
    """
    user = await user_service.authenticate_user(email, password)
    if not user:
        raise UnauthorizedException(detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    logger.info(f"Token issued for user: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New User",
    dependencies=[Depends(get_current_active_superuser)] # Only superusers can create users
)
async def create_user(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Creates a new user in the system.
    Requires superuser privileges.
    """
    try:
        new_user = await user_service.create_user(user_create)
        logger.info(f"API: User {new_user.email} created by superuser.")
        return new_user
    except ConflictException as e:
        raise e
    except Exception as e:
        logger.error(f"API: Error creating user {user_create.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user creation.")

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get User by ID",
    dependencies=[Depends(get_current_active_user)] # Any active user can view
)
async def get_user_by_id(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieves a user's details by their ID.
    Requires authentication.
    """
    try:
        user = await user_service.get_user_by_id(user_id)
        logger.debug(f"API: Retrieved user ID {user_id}.")
        return user
    except NotFoundException as e:
        raise e
    except Exception as e:
        logger.error(f"API: Error retrieving user ID {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user retrieval.")

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="Get All Users",
    dependencies=[Depends(get_current_active_superuser)] # Only superusers can list all users
)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieves a list of all users with pagination.
    Requires superuser privileges.
    """
    try:
        users = await user_service.get_all_users(skip=skip, limit=limit)
        logger.debug(f"API: Retrieved {len(users)} users.")
        return users
    except Exception as e:
        logger.error(f"API: Error retrieving all users: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user list retrieval.")

@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update User",
    dependencies=[Depends(get_current_active_superuser)] # Only superusers can update users
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Updates an existing user's information.
    Requires superuser privileges.
    """
    try:
        updated_user = await user_service.update_user(user_id, user_update)
        logger.info(f"API: User ID {user_id} updated by superuser.")
        return updated_user
    except NotFoundException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        logger.error(f"API: Error updating user ID {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user update.")

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User",
    dependencies=[Depends(get_current_active_superuser)] # Only superusers can delete users
)
async def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    """
    Deletes a user from the system.
    Requires superuser privileges.
    """
    try:
        await user_service.delete_user(user_id)
        logger.info(f"API: User ID {user_id} deleted by superuser.")
        return {"message": "User deleted successfully"} # FastAPI returns 204 for no content
    except NotFoundException as e:
        raise e
    except Exception as e:
        logger.error(f"API: Error deleting user ID {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user deletion.")