from fastapi import APIRouter, Depends, status, Query
from typing import List

from schemas import RoleCreate, RoleResponse, PermissionCreate, PermissionResponse, UserResponse, MessageResponse
from services.user_service import UserService, get_user_service
from core.security import get_current_user
from rbac import get_rbac, RBAC
from core.exceptions import NotFoundException, ConflictException
from core.logging_config import setup_logging

logger = setup_logging()

router = APIRouter()

# All endpoints in this router require the 'admin' role or specific permissions
# We'll use a general admin role check for simplicity, but specific permissions could be used too.

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, summary="Create a new role (Admin only)")
async def create_role(
    role_in: RoleCreate,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Creates a new role with optional permissions.
    Requires 'admin' role or 'role:create' permission.
    """
    rbac.has_permission(["role:create"])(current_user) # Or rbac.has_role(["admin"])
    logger.info(f"Admin user {current_user.user_id} attempting to create role: {role_in.name}")
    new_role = user_service.create_role(role_in)
    logger.info(f"Role '{new_role.name}' created by admin {current_user.user_id}.")
    return new_role

@router.get("/roles", response_model=List[RoleResponse], summary="Get all roles (Admin only)")
async def get_all_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Retrieves a list of all roles with pagination.
    Requires 'admin' role or 'role:read' permission.
    """
    rbac.has_permission(["role:read"])(current_user) # Or rbac.has_role(["admin"])
    logger.info(f"Admin user {current_user.user_id} retrieving all roles.")
    roles = user_service.get_roles(skip=skip, limit=limit)
    return roles

@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED, summary="Create a new permission (Admin only)")
async def create_permission(
    permission_in: PermissionCreate,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Creates a new permission.
    Requires 'admin' role or 'permission:create' permission.
    """
    rbac.has_permission(["permission:create"])(current_user) # Or rbac.has_role(["admin"])
    logger.info(f"Admin user {current_user.user_id} attempting to create permission: {permission_in.name}")
    new_permission = user_service.create_permission(permission_in)
    logger.info(f"Permission '{new_permission.name}' created by admin {current_user.user_id}.")
    return new_permission

@router.get("/permissions", response_model=List[PermissionResponse], summary="Get all permissions (Admin only)")
async def get_all_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Retrieves a list of all permissions with pagination.
    Requires 'admin' role or 'permission:read' permission.
    """
    rbac.has_permission(["permission:read"])(current_user) # Or rbac.has_role(["admin"])
    logger.info(f"Admin user {current_user.user_id} retrieving all permissions.")
    permissions = user_service.get_permissions(skip=skip, limit=limit)
    return permissions

@router.post("/users/{user_id}/roles/{role_id}", response_model=UserResponse, summary="Assign a role to a user (Admin only)")
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Assigns a specific role to a user.
    Requires 'admin' role or 'user:assign_role' permission.
    """
    rbac.has_permission(["user:assign_role"])(current_user) # Or rbac.has_role(["admin"])
    logger.info(f"Admin user {current_user.user_id} attempting to assign role {role_id} to user {user_id}.")
    updated_user = user_service.assign_role_to_user(user_id, role_id)
    logger.info(f"Role {role_id} assigned to user {user_id} by admin {current_user.user_id}.")
    return updated_user

@router.delete("/users/{user_id}/roles/{role_id}", response_model=UserResponse, summary="Remove a role from a user (Admin only)")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: TokenData = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    rbac: RBAC = Depends(get_rbac)
):
    """
    Removes a specific role from a user.
    Requires 'admin' role or 'user:remove_role' permission.
    """
    rbac.has_permission(["user:remove_role"])(current_user) # Or rbac.has_role(["admin"])
    logger.info(f"Admin user {current_user.user_id} attempting to remove role {role_id} from user {user_id}.")
    updated_user = user_service.remove_role_from_user(user_id, role_id)
    logger.info(f"Role {role_id} removed from user {user_id} by admin {current_user.user_id}.")
    return updated_user