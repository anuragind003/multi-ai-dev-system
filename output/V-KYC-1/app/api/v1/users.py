import logging
from typing import List

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app import crud
from app.core.exceptions import NotFoundException
from app.dependencies import get_db, get_current_active_user, get_current_admin_user
from app.schemas import MessageResponse, TokenData, UserResponse, UserUpdate
from app.models import UserRole

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/me", response_model=UserResponse, summary="Get current user's profile")
async def read_current_user(
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the profile details of the currently authenticated user.
    """
    user = crud.get_user(db, user_id=current_user.user_id)
    if not user:
        # This case should ideally not happen if token is valid and user exists
        logger.error(f"Authenticated user {current_user.email} (ID: {current_user.user_id}) not found in DB.")
        raise NotFoundException("Authenticated user not found.")
    return user

@router.put("/me", response_model=UserResponse, summary="Update current user's profile")
async def update_current_user(
    user_update: UserUpdate,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Updates the profile details of the currently authenticated user.
    Users can only update their own `full_name`.
    `is_active` and `role` fields can only be updated by an Admin.
    """
    logger.info(f"User {current_user.email} attempting to update their profile.")

    # Prevent non-admin users from changing active status or role
    if user_update.is_active is not None and UserRole.ADMIN not in current_user.roles:
        user_update.is_active = None # Ignore the update
        logger.warning(f"User {current_user.email} attempted to change is_active status without admin rights.")
    if user_update.role is not None and UserRole.ADMIN not in current_user.roles:
        user_update.role = None # Ignore the update
        logger.warning(f"User {current_user.email} attempted to change role without admin rights.")

    updated_user = crud.update_user(db, user_id=current_user.user_id, user_update=user_update)
    return updated_user

@router.get("/", response_model=List[UserResponse], summary="Get all users (Admin only)")
async def read_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: TokenData = Depends(get_current_admin_user), # Requires admin role
    db: Session = Depends(get_db)
):
    """
    Retrieves a list of all registered users.
    Requires Admin role.
    """
    logger.info(f"Admin user {current_user.email} requesting all users.")
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID (Admin only)")
async def read_user_by_id(
    user_id: int = Path(..., description="The ID of the user to retrieve"),
    current_user: TokenData = Depends(get_current_admin_user), # Requires admin role
    db: Session = Depends(get_db)
):
    """
    Retrieves a single user's profile by their ID.
    Requires Admin role.
    """
    logger.info(f"Admin user {current_user.email} requesting user ID: {user_id}")
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise NotFoundException(f"User with ID {user_id} not found.")
    return user

@router.put("/{user_id}", response_model=UserResponse, summary="Update user by ID (Admin only)")
async def update_user_by_id(
    user_id: int = Path(..., description="The ID of the user to update"),
    user_update: UserUpdate,
    current_user: TokenData = Depends(get_current_admin_user), # Requires admin role
    db: Session = Depends(get_db)
):
    """
    Updates a user's profile by their ID.
    Requires Admin role.
    """
    logger.info(f"Admin user {current_user.email} attempting to update user ID: {user_id}")
    updated_user = crud.update_user(db, user_id=user_id, user_update=user_update)
    return updated_user

@router.delete("/{user_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK, summary="Delete user by ID (Admin only)")
async def delete_user_by_id(
    user_id: int = Path(..., description="The ID of the user to delete"),
    current_user: TokenData = Depends(get_current_admin_user), # Requires admin role
    db: Session = Depends(get_db)
):
    """
    Deletes a user by their ID.
    Requires Admin role.
    """
    logger.warning(f"Admin user {current_user.email} attempting to delete user ID: {user_id}")
    crud.delete_user(db, user_id=user_id)
    return {"message": f"User with ID {user_id} deleted successfully."}