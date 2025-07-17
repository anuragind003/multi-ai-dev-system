import logging
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import UserResponse, UserUpdate, HTTPError
from services.user_service import UserService
from core.security import get_current_active_user, get_current_active_admin
from core.exceptions import NotFoundException, ConflictException, ForbiddenException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user's profile",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Inactive user"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def read_users_me(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Retrieves the profile of the currently authenticated user.
    Requires a valid JWT token.
    """
    logger.info(f"User '{current_user.username}' accessed their own profile.")
    return current_user

@router.get(
    "/",
    response_model=List[UserResponse],
    summary="Get all users (Admin only)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Not enough permissions"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def read_all_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_admin) # Requires admin role
):
    """
    Retrieves a list of all users in the system.
    This endpoint is restricted to users with 'admin' role.
    - **skip**: Number of records to skip for pagination.
    - **limit**: Maximum number of records to return.
    """
    user_service = UserService(db)
    users = await user_service.get_all_users(skip=skip, limit=limit)
    logger.info(f"Admin user '{current_user.username}' fetched {len(users)} users.")
    return users

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user by ID (Admin only)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Not enough permissions"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: User not found"},
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "Conflict: Username or email already taken"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def update_user_by_id(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_admin) # Requires admin role
):
    """
    Updates an existing user's information by their ID.
    This endpoint is restricted to users with 'admin' role.
    - **user_id**: The ID of the user to update.
    - **user_in**: The updated user data.
    """
    user_service = UserService(db)
    try:
        updated_user = await user_service.update_user(user_id, user_in)
        logger.info(f"Admin user '{current_user.username}' updated user ID {user_id}.")
        return updated_user
    except NotFoundException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred while updating user ID {user_id}: {e}")
        raise

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user by ID (Admin only)",
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "User successfully deleted"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Not enough permissions"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: User not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def delete_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_admin) # Requires admin role
):
    """
    Deletes a user by their ID.
    This endpoint is restricted to users with 'admin' role.
    - **user_id**: The ID of the user to delete.
    """
    user_service = UserService(db)
    deleted = await user_service.delete_user(user_id)
    if not deleted:
        raise NotFoundException(detail=f"User with ID {user_id} not found.")
    logger.info(f"Admin user '{current_user.username}' deleted user ID {user_id}.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)