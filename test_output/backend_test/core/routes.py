"""
API Routes and Controllers
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from core.models import User, UserCreate, Item, ItemCreate
from core.services import UserService, ItemService

router = APIRouter()

# User routes
@router.post("/users/", response_model=User)
async def create_user(user: UserCreate):
    """Create a new user."""
    return await UserService.create_user(user)

@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get user by ID."""
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users/", response_model=List[User])
async def list_users(skip: int = 0, limit: int = 100):
    """List users with pagination."""
    return await UserService.list_users(skip=skip, limit=limit)

# Item routes
@router.post("/items/", response_model=Item)
async def create_item(item: ItemCreate, owner_id: int):
    """Create a new item."""
    return await ItemService.create_item(item, owner_id)

@router.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Get item by ID."""
    item = await ItemService.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.get("/items/", response_model=List[Item])
async def list_items(skip: int = 0, limit: int = 100):
    """List items with pagination."""
    return await ItemService.list_items(skip=skip, limit=limit)
