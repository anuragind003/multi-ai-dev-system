from typing import List
from fastapi import Depends, status
from sqlalchemy.orm import Session

from models import User, UserRole
from security import get_current_user
from utils.exceptions import HTTPForbidden
from utils.logger import logger

class RoleChecker:
    """
    FastAPI dependency to check if the current user has one of the required roles.
    """
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        """
        Checks if the current user's role is in the list of allowed roles.
        """
        if not current_user.role:
            logger.warning(f"User {current_user.username} has no role assigned.")
            raise HTTPForbidden(detail="User has no assigned role.")

        if current_user.role.name not in self.allowed_roles:
            logger.warning(f"User {current_user.username} with role '{current_user.role.name.value}' attempted to access resource requiring roles: {', '.join([r.value for r in self.allowed_roles])}")
            raise HTTPForbidden(detail="You do not have the necessary permissions to access this resource.")
        
        logger.info(f"User {current_user.username} with role '{current_user.role.name.value}' successfully authorized for resource.")
        return current_user

# Pre-defined role checkers for convenience
requires_team_lead = RoleChecker([UserRole.TEAM_LEAD])
requires_process_manager = RoleChecker([UserRole.PROCESS_MANAGER])
requires_any_vkyc_role = RoleChecker([UserRole.TEAM_LEAD, UserRole.PROCESS_MANAGER])