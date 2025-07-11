from typing import List, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.exceptions import ForbiddenException, UnauthorizedException
from core.security import get_current_user
from database import get_db
from models import User, Role, Permission
from schemas import TokenData
from core.logging_config import setup_logging

logger = setup_logging()

class RBAC:
    """
    Role-Based Access Control (RBAC) manager.
    Provides methods to check user permissions based on their roles.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_user_permissions(self, user_id: int) -> Set[str]:
        """
        Retrieves all unique permissions for a given user ID.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"RBAC: User with ID {user_id} not found.")
            return set()

        permissions: Set[str] = set()
        for role in user.roles:
            for permission in role.permissions:
                permissions.add(permission.name)
        
        logger.debug(f"RBAC: User {user_id} has permissions: {permissions}")
        return permissions

    def has_permission(self, required_permissions: List[str]):
        """
        FastAPI dependency to check if the current user has any of the required permissions.
        If the user has multiple roles, permissions are aggregated.
        """
        def permission_checker(current_user: TokenData = Depends(get_current_user)):
            if not current_user:
                raise UnauthorizedException(detail="Not authenticated")

            user_permissions = set(current_user.permissions)
            
            # If no specific permissions are required, just being authenticated is enough
            if not required_permissions:
                return True

            # Check if the user has at least one of the required permissions
            for req_perm in required_permissions:
                if req_perm in user_permissions:
                    logger.debug(f"RBAC: User {current_user.user_id} has required permission '{req_perm}'. Access granted.")
                    return True
            
            logger.warning(f"RBAC: User {current_user.user_id} (roles: {current_user.roles}) lacks required permissions: {required_permissions}. User permissions: {user_permissions}. Access denied.")
            raise ForbiddenException(detail="Not enough permissions to perform this action.")
        return permission_checker

    def has_role(self, required_roles: List[str]):
        """
        FastAPI dependency to check if the current user has any of the required roles.
        """
        def role_checker(current_user: TokenData = Depends(get_current_user)):
            if not current_user:
                raise UnauthorizedException(detail="Not authenticated")
            
            user_roles = set(current_user.roles)

            # If no specific roles are required, just being authenticated is enough
            if not required_roles:
                return True

            # Check if the user has at least one of the required roles
            for req_role in required_roles:
                if req_role in user_roles:
                    logger.debug(f"RBAC: User {current_user.user_id} has required role '{req_role}'. Access granted.")
                    return True
            
            logger.warning(f"RBAC: User {current_user.user_id} lacks required roles: {required_roles}. User roles: {user_roles}. Access denied.")
            raise ForbiddenException(detail="Not authorized for this role.")
        return role_checker

# Dependency to inject RBAC instance
def get_rbac(db: Session = Depends(get_db)) -> RBAC:
    return RBAC(db)