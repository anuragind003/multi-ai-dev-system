from fastapi import APIRouter, Depends, status
from typing import Annotated

from schemas import UserResponse, HTTPError
from core.security import get_current_user
from models import User
from utils.logger import setup_logging

logger = setup_logging()

router = APIRouter()

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user's details",
    responses={
        status.HTTP_200_OK: {"model": UserResponse, "description": "Current user details"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
    }
)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves the details of the currently authenticated user.
    Requires a valid JWT token in the Authorization header.
    """
    logger.info(f"Fetching details for current user: {current_user.email}")
    return current_user