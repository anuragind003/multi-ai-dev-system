from typing import List
from fastapi import APIRouter, Depends, status, HTTPException, Path, Query
import logging

from schemas import UserResponse, UserUpdate, HTTPError
from services.auth_service import AuthService
from core.dependencies import get_auth_service, get_current_admin_user, get_current_active_user
from models import User
from core.exceptions import NotFoundException, ConflictException, ForbiddenException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user's details",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden"}
    }
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves the details of the currently authenticated user.
    """
    return current_user

@router.get(
    "/",
    response_model=List[UserResponse],
    summary="Get all users (Admin only)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires Admin role"}
    }
)
async def read_users(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_admin_user) # Requires admin role
):
    """
    Retrieves a list of all users in the system.
    This endpoint is restricted to users with the 'admin' role.
    """
    users = await auth_service.user_crud.get_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(user) for user in users]

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (Admin or self-access)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Not authorized to view this user"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: User not found"}
    }
)
async def read_user_by_id(
    user_id: int = Path(..., ge=1, description="The ID of the user to retrieve"),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves a specific user by their ID.
    Only 'admin' users can view any user. 'qa_engineer' users can only view their own profile.
    """
    if current_user.role != "admin" and current_user.id != user_id:
        raise ForbiddenException("You are not authorized to view this user's profile.")

    user = await auth_service.user_crud.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    return UserResponse.model_validate(user)

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user by ID (Admin or self-update)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Not authorized to update this user"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: User not found"},
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "Conflict: Username or email already exists"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def update_user(
    user_id: int = Path(..., ge=1, description="The ID of the user to update"),
    user_in: UserUpdate,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Updates an existing user's information.
    Only 'admin' users can update any user. 'qa_engineer' users can only update their own profile.
    'qa_engineer' users cannot change their own role.
    """
    if current_user.role != "admin" and current_user.id != user_id:
        raise ForbiddenException("You are not authorized to update this user.")
    
    if current_user.role != "admin" and user_in.role is not None and user_in.role != current_user.role:
        raise ForbiddenException("You are not authorized to change your own role.")

    hashed_password = None
    if user_in.password:
        from core.security import get_password_hash # Import locally to avoid circular dependency
        hashed_password = get_password_hash(user_in.password)

    try:
        updated_user = await auth_service.user_crud.update_user(user_id, user_in, hashed_password)
        logger.info(f"User {user_id} updated by {current_user.username}.")
        return UserResponse.model_validate(updated_user)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user update.")

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user by ID (Admin only)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires Admin role"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: User not found"}
    }
)
async def delete_user(
    user_id: int = Path(..., ge=1, description="The ID of the user to delete"),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_admin_user) # Requires admin role
):
    """
    Deletes a user from the system.
    This endpoint is restricted to users with the 'admin' role.
    """
    if current_user.id == user_id:
        raise ForbiddenException("You cannot delete your own user account.")
        
    try:
        await auth_service.user_crud.delete_user(user_id)
        logger.info(f"User {user_id} deleted by admin {current_user.username}.")
        return {"message": "User deleted successfully."}
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during user deletion.")