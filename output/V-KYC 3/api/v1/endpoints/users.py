import logging
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import UserResponse
from services.user_service import UserService
from core.dependencies import get_current_active_user, get_current_superuser
from models import User # Import User model for type hinting in dependencies

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/me", response_model=UserResponse, summary="Get Current Authenticated User")
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves the details of the currently authenticated user.
    Requires a valid access token.
    """
    logger.info(f"Fetching details for current user: {current_user.username}")
    return UserResponse.model_validate(current_user)

@router.get("/", response_model=List[UserResponse], summary="Get All Users (Admin Only)")
async def read_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser) # Requires superuser role
):
    """
    Retrieves a list of all users in the system.
    This endpoint is restricted to superusers only.
    """
    logger.info(f"Admin user '{current_user.username}' is fetching all users.")
    user_service = UserService(db)
    users = await user_service.get_all_users()
    logger.info(f"Retrieved {len(users)} users.")
    return users