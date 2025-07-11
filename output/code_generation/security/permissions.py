from fastapi import Depends, HTTPException, status
from typing import List

from core.exceptions import ForbiddenException
from utils.logger import get_logger
from security.auth import get_current_user # Import get_current_user from auth.py

logger = get_logger(__name__)

class RoleChecker:
    """
    A dependency class for role-based access control.
    Checks if the current authenticated user has at least one of the required roles.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
        logger.debug(f"RoleChecker initialized with allowed roles: {allowed_roles}")

    async def __call__(self, current_user: dict = Depends(get_current_user)):
        """
        The actual dependency function that performs the role check.

        Args:
            current_user (dict): The authenticated user's information (from get_current_user).

        Raises:
            ForbiddenException: If the user does not have any of the required roles.
        """
        user_roles = set(current_user.get("roles", []))
        
        if not user_roles.intersection(self.allowed_roles):
            logger.warning(
                f"Access denied for user '{current_user['username']}'. "
                f"Required roles: {self.allowed_roles}, User roles: {list(user_roles)}"
            )
            raise ForbiddenException(detail="Not enough permissions to perform this action.")
        
        logger.debug(f"User '{current_user['username']}' has required roles for access.")
        return True # Access granted