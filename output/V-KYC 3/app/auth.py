from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Role, Permission, RolePermission
from app.schemas import TokenData
from app.security import verify_token
from app.exceptions import UnauthorizedException, ForbiddenException
from app.logger import logger

# OAuth2PasswordBearer for handling token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current authenticated user.
    Decodes the JWT token, verifies it, and fetches the user from the database.
    Raises UnauthorizedException if token is invalid or user not found/inactive.
    """
    token_data: TokenData
    try:
        payload = verify_token(token)
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise UnauthorizedException(detail="Could not validate credentials", message="Invalid token payload")
        token_data = TokenData(email=email)
    except UnauthorizedException as e:
        raise e # Re-raise the specific UnauthorizedException
    except Exception as e:
        logger.error(f"Error processing token: {e}")
        raise UnauthorizedException(detail="Could not validate credentials", message="Token processing error")

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        logger.warning(f"User not found for token email: {token_data.email}")
        raise UnauthorizedException(detail="User not found", message="Invalid credentials")
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.email}")
        raise UnauthorizedException(detail="Inactive user", message="User account is inactive")

    return user

def has_role(role_names: List[str]):
    """
    Dependency factory to check if the current user has any of the specified roles.
    Args:
        role_names: A list of role names (e.g., ["admin", "auditor"])
    Returns:
        A dependency function that raises ForbiddenException if the user does not have the required role.
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if not current_user.role:
            logger.warning(f"User {current_user.email} has no assigned role.")
            raise ForbiddenException(detail="User has no assigned role.")

        if current_user.role.name not in role_names:
            logger.warning(f"User {current_user.email} (Role: {current_user.role.name}) attempted access without required roles: {role_names}")
            raise ForbiddenException(detail=f"User does not have required role. Required: {', '.join(role_names)}", message="Insufficient permissions")
        return current_user
    return role_checker

def has_permission(permission_name: str):
    """
    Dependency factory to check if the current user has a specific permission.
    Permissions are derived from the user's assigned role.
    Args:
        permission_name: The name of the permission (e.g., "recording:download")
    Returns:
        A dependency function that raises ForbiddenException if the user does not have the required permission.
    """
    def permission_checker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        if not current_user.role:
            logger.warning(f"User {current_user.email} has no assigned role.")
            raise ForbiddenException(detail="User has no assigned role.")

        # Eagerly load permissions for the user's role
        user_role_with_permissions = db.query(Role).filter(Role.id == current_user.role_id).options(
            # Join and load permissions through the association table
            # This ensures permissions are loaded with the role in one query
            # and are accessible via role.role_permissions -> permission
            relationship.contains_eager(Role.role_permissions).contains_eager(RolePermission.permission)
        ).first()

        if not user_role_with_permissions:
            logger.error(f"Role ID {current_user.role_id} not found for user {current_user.email}.")
            raise ForbiddenException(detail="User's role not found or misconfigured.")

        # Check if the required permission exists within the user's role's permissions
        has_required_permission = any(
            rp.permission.name == permission_name
            for rp in user_role_with_permissions.role_permissions
            if rp.permission
        )

        if not has_required_permission:
            logger.warning(f"User {current_user.email} (Role: {current_user.role.name}) attempted access without required permission: {permission_name}")
            raise ForbiddenException(detail=f"User does not have required permission: {permission_name}", message="Insufficient permissions")
        return current_user
    return permission_checker