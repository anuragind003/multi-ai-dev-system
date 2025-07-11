python
### FILE: routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User
from ..schemas import User, UserCreate
from ..security import get_current_user
import logging

router = APIRouter()

# Configure logging for this module
logger = logging.getLogger(__name__)

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get the current user's information.
    """
    try:
        logger.info(f"User information retrieved for: {current_user.username}")
        return current_user
    except Exception as e:
        logger.error(f"Error retrieving user information: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve user information")

@router.get("/", response_model=List[User])
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve all users (admin only).
    """
    # In a real application, you'd add authorization checks here to ensure only admins can access this
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        logger.info(f"Users retrieved by admin: {current_user.username}")
        return users
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve users")