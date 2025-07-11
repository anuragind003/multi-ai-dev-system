from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from schemas import UserResponse, UserCreate # UserCreate used for update as it has password field
from services import user_service
from database import get_db
from core.security import get_current_active_user, require_roles
from core.exceptions import NotFoundException, ForbiddenException
from models import User, UserRole
from loguru import logger

router = APIRouter(prefix="/users", tags=["Users"])

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user's profile",
    description="Retrieves the profile details of the currently authenticated user."
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current authenticated user's profile.
    Requires a valid JWT token.
    """
    logger.info(f"User '{current_user.username}' requested their own profile.")
    return UserResponse.model_validate(current_user)

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user profile by ID (Admin only)",
    description="Retrieves the profile details of a specific user by ID. Requires 'admin' role."
)
async def read_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Get a user's profile by ID.
    Requires 'admin' role.
    - **user_id**: The ID of the user to retrieve.
    """
    logger.info(f"Admin user '{current_user.username}' requested profile for user ID: {user_id}.")
    try:
        user = user_service.get_user_profile(db, user_id)
        return user
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Error retrieving user ID {user_id} by admin {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user profile (Admin or self)",
    description="Updates the profile details of a user. Admins can update any user; regular users can only update their own profile. Admins can also change roles and activation status."
)
async def update_user_profile(
    user_id: int,
    user_update: UserCreate, # Re-using UserCreate for update, adjust as needed for partial updates
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a user's profile.
    - **user_id**: The ID of the user to update.
    - **user_update**: The updated user data.
    """
    logger.info(f"User '{current_user.username}' attempting to update user ID: {user_id}.")
    try:
        # Convert Pydantic model to dict, excluding unset fields for partial update
        update_data = user_update.model_dump(exclude_unset=True)
        updated_user = user_service.update_user_profile(db, user_id, update_data, current_user)
        return updated_user
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        logger.error(f"Error updating user ID {user_id} by {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during update.")