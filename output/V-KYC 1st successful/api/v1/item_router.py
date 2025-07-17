import logging
from typing import List

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import ItemCreate, ItemResponse, HTTPError, UserResponse
from services.item_service import ItemService
from core.security import get_current_active_user
from core.exceptions import NotFoundException, BadRequestException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Inactive user"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def create_item(
    item_in: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Creates a new item associated with the current authenticated user.
    - **title**: Title of the item.
    - **description**: Optional description of the item.
    """
    item_service = ItemService(db)
    try:
        new_item = await item_service.create_item(item_in, current_user.id)
        logger.info(f"User '{current_user.username}' created item '{new_item.title}'.")
        return new_item
    except Exception as e:
        logger.exception(f"An unexpected error occurred during item creation: {e}")
        raise

@router.get(
    "/",
    response_model=List[ItemResponse],
    summary="Get all items",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Inactive user"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def read_all_items(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user) # Protected route
):
    """
    Retrieves a list of all items in the system.
    Requires a valid JWT token.
    - **skip**: Number of records to skip for pagination.
    - **limit**: Maximum number of records to return.
    """
    item_service = ItemService(db)
    items = await item_service.get_all_items(skip=skip, limit=limit)
    logger.info(f"User '{current_user.username}' fetched {len(items)} items.")
    return items

@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get item by ID",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Inactive user"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Item not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def read_item_by_id(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user) # Protected route
):
    """
    Retrieves a single item by its ID.
    Requires a valid JWT token.
    - **item_id**: The ID of the item to retrieve.
    """
    item_service = ItemService(db)
    item = await item_service.get_item_by_id(item_id)
    if not item:
        raise NotFoundException(detail=f"Item with ID {item_id} not found.")
    logger.info(f"User '{current_user.username}' fetched item ID {item_id}.")
    return item

@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Update item by ID",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Inactive user or not authorized to update"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Item not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def update_item_by_id(
    item_id: int,
    item_in: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Updates an existing item by its ID. Only the owner can update their item.
    - **item_id**: The ID of the item to update.
    - **item_in**: The updated item data.
    """
    item_service = ItemService(db)
    try:
        updated_item = await item_service.update_item(item_id, item_in, current_user.id)
        logger.info(f"User '{current_user.username}' updated item ID {item_id}.")
        return updated_item
    except NotFoundException as e:
        raise e
    except BadRequestException as e: # For unauthorized update
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred while updating item ID {item_id}: {e}")
        raise

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item by ID",
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Item successfully deleted"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Inactive user or not authorized to delete"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Item not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal Server Error"}
    }
)
async def delete_item_by_id(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Deletes an item by its ID. Only the owner can delete their item.
    - **item_id**: The ID of the item to delete.
    """
    item_service = ItemService(db)
    try:
        deleted = await item_service.delete_item(item_id, current_user.id)
        if not deleted:
            raise NotFoundException(detail=f"Item with ID {item_id} not found.")
        logger.info(f"User '{current_user.username}' deleted item ID {item_id}.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except BadRequestException as e: # For unauthorized delete
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred while deleting item ID {item_id}: {e}")
        raise