from fastapi import APIRouter, Depends, status, Query
from typing import List

from schemas import UserResponse, UserUpdate, MessageResponse, TokenData
from services.user_service import UserService, get_user_service
from core.security import get_current_user
from rbac import get_rbac, RBAC
from core.exceptions import NotFoundException, ForbiddenException, ConflictException
from core.logging_config import setup_logging

logger = setup_logging()

router = APIRouter()

@router.get("/me", response_model=UserResponse, summary="Get current authenticated user's profile")
async def read_users_me(
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieves the profile of the currently authenticated user.
    Requires authentication.
    """
    user = user_service.get_user_by_id(current_user.user_id)
    if not user:
        logger.error(f"Authenticated user ID {current_user.user_id} not found in DB. This should not happen.")
        raise NotFoundException(detail="Authenticated user not found.")
    return user

@router.put("/me", response_model=UserResponse, summary="Update current authenticated user's profile")
async def update_users_me(
    user_in: UserUpdate,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Updates the profile of the currently authenticated user.
    - **email**: New email address (optional).
    - **password**: New password (optional).
    - **is_active**: Account status (optional).
    Requires authentication.
    """
    logger.info(f"User {current_user.user_id} attempting to update their profile.")
    # Ensure users cannot change their own roles via this endpoint
    if user_in.role_ids is not None:
        logger.warning(f"User {current_user.user_id} attempted to modify their own roles via /me endpoint.")
        raise ForbiddenException(detail="You cannot modify your own roles via this endpoint.")
    
    updated_user = user_service.update_user(current_user.user_id, user_in)
    logger.info(f"User {current_user.user_id} profile updated successfully.")
    return updated_user

@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID (Admin/User:Read permission required)")
async def get_user_by_id(
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Retrieves a user by their ID.
    Requires 'user:read' permission or 'admin' role.
    Users can retrieve their own profile without 'user:read' permission.
    """
    if current_user.user_id == user_id:
        # Allow users to view their own profile
        logger.info(f"User {current_user.user_id} accessing their own profile.")
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        return user
    else:
        # For other users, check permissions
        rbac.has_permission(["user:read"])(current_user) # This will raise ForbiddenException if not met
        logger.info(f"User {current_user.user_id} accessing user {user_id}'s profile.")
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        return user

@router.get("/", response_model=List[UserResponse], summary="Get all users (Admin/User:Read permission required)")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Retrieves a list of all users with pagination.
    Requires 'user:read' permission.
    """
    rbac.has_permission(["user:read"])(current_user)
    logger.info(f"User {current_user.user_id} retrieving all users (skip={skip}, limit={limit}).")
    users = user_service.get_users(skip=skip, limit=limit)
    return users

@router.put("/{user_id}", response_model=UserResponse, summary="Update user by ID (Admin/User:Write permission required)")
async def update_user_by_id(
    user_id: int,
    user_in: UserUpdate,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Updates a user's information by their ID.
    Requires 'user:write' permission.
    """
    rbac.has_permission(["user:write"])(current_user)
    logger.info(f"User {current_user.user_id} attempting to update user {user_id}.")
    updated_user = user_service.update_user(user_id, user_in)
    logger.info(f"User {user_id} updated successfully by {current_user.user_id}.")
    return updated_user

@router.delete("/{user_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK, summary="Delete user by ID (Admin/User:Delete permission required)")
async def delete_user_by_id(
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Deletes a user by their ID.
    Requires 'user:delete' permission.
    """
    rbac.has_permission(["user:delete"])(current_user)
    logger.info(f"User {current_user.user_id} attempting to delete user {user_id}.")
    if current_user.user_id == user_id:
        logger.warning(f"User {current_user.user_id} attempted to delete their own account.")
        raise ForbiddenException(detail="You cannot delete your own account.")
        
    user_service.delete_user(user_id)
    logger.info(f"User {user_id} deleted successfully by {current_user.user_id}.")
    return {"message": f"User with ID {user_id} deleted successfully."}