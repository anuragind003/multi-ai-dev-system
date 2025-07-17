from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.schemas import UserResponse, ItemCreate, ItemResponse, MessageResponse
from app.models import User
from app.db import get_db
from app.security import get_current_active_user, get_current_active_superuser
from app.services import user_service, item_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieves the profile of the currently authenticated user.",
    responses={
        401: {"model": MessageResponse, "description": "Unauthorized - Not authenticated"},
        403: {"model": MessageResponse, "description": "Forbidden - Inactive user"}
    }
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the profile of the authenticated user.
    Requires a valid JWT token.
    """
    logger.info(f"Fetching profile for user ID: {current_user.id}")
    return await user_service.get_user_profile(db, current_user.id)

@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
    description="Creates a new item associated with the current authenticated user.",
    responses={
        401: {"model": MessageResponse, "description": "Unauthorized - Not authenticated"},
        403: {"model": MessageResponse, "description": "Forbidden - Inactive user"},
        422: {"model": MessageResponse, "description": "Validation Error"}
    }
)
async def create_item_for_current_user(
    item_in: ItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates an item for the current authenticated user.
    - **item_in**: Item details (title, description).
    """
    logger.info(f"User {current_user.id} attempting to create item: {item_in.title}")
    item = await item_service.create_user_item(db, item_in, current_user.id)
    logger.info(f"Item '{item.title}' created by user {current_user.id}.")
    return item

@router.get(
    "/items",
    response_model=List[ItemResponse],
    summary="Get all items",
    description="Retrieves a list of all items. Accessible by authenticated users.",
    responses={
        401: {"model": MessageResponse, "description": "Unauthorized - Not authenticated"},
        403: {"model": MessageResponse, "description": "Forbidden - Inactive user"}
    }
)
async def read_all_items(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user), # Requires authentication
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of all items in the system.
    """
    logger.info(f"User {current_user.id} fetching all items (skip={skip}, limit={limit}).")
    items = await item_service.get_all_items(db, skip=skip, limit=limit)
    return items

@router.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Get item by ID",
    description="Retrieves details of a specific item by its ID. Accessible by authenticated users.",
    responses={
        401: {"model": MessageResponse, "description": "Unauthorized - Not authenticated"},
        403: {"model": MessageResponse, "description": "Forbidden - Inactive user"},
        404: {"model": MessageResponse, "description": "Not Found - Item not found"}
    }
)
async def read_item_by_id(
    item_id: int,
    current_user: User = Depends(get_current_active_user), # Requires authentication
    db: AsyncSession = Depends(get_db)
):
    """
    Returns details of a specific item.
    - **item_id**: The ID of the item to retrieve.
    """
    logger.info(f"User {current_user.id} fetching item with ID: {item_id}")
    item = await item_service.get_item_details(db, item_id)
    return item

@router.get(
    "/admin/users",
    response_model=List[UserResponse],
    summary="Get all users (Admin only)",
    description="Retrieves a list of all users. Requires superuser privileges.",
    responses={
        401: {"model": MessageResponse, "description": "Unauthorized - Not authenticated"},
        403: {"model": MessageResponse, "description": "Forbidden - Not a superuser"}
    }
)
async def read_all_users(
    skip: int = 0,
    limit: int = 100,
    current_superuser: User = Depends(get_current_active_superuser), # Requires superuser
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of all users in the system.
    Only accessible by superusers.
    """
    logger.info(f"Superuser {current_superuser.id} fetching all users (skip={skip}, limit={limit}).")
    # This would typically be a new CRUD/Service method for admin operations
    # For simplicity, we'll just fetch users directly here.
    users = await db.execute(
        db.query(User).offset(skip).limit(limit)
    )
    return [UserResponse.model_validate(user) for user in users.scalars().all()]