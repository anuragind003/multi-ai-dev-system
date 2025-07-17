### FILE: routes/users.py
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from database import get_db
from schemas import UserCreate, UserResponse, UserUpdate, RoleCreate, RoleResponse
from services import UserService, RoleService
from auth import role_required
from utils.logger import logger

router = APIRouter(prefix="/users", tags=["Users & Roles"])

# --- User Endpoints ---
@router.post(
    "/",
    response_model=UserResponse,
    summary="Create a new user",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(role_required(["admin"]))] # Only 'admin' can create users
)
async def create_user_endpoint(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new user in the system.
    Requires 'admin' role.
    """
    logger.info(f"Admin attempting to create user: {user.username}")
    return await UserService.create_user(db, user)

@router.get(
    "/",
    response_model=List[UserResponse],
    summary="Get all users",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(role_required(["admin", "process_manager"]))] # 'admin' or 'process_manager' can view all users
)
async def read_users_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a list of all users.
    Requires 'admin' or 'process_manager' role.
    """
    logger.info(f"Fetching all users (skip={skip}, limit={limit})")
    return await UserService.get_all_users(db, skip=skip, limit=limit)

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(role_required(["admin", "process_manager"]))] # 'admin' or 'process_manager' can view specific users
)
async def read_user_by_id_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a single user by their ID.
    Requires 'admin' or 'process_manager' role.
    """
    logger.info(f"Fetching user with ID: {user_id}")
    return await UserService.get_user_by_id(db, user_id)

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(role_required(["admin"]))] # Only 'admin' can update users
)
async def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Updates an existing user's details.
    Requires 'admin' role.
    """
    logger.info(f"Admin attempting to update user with ID: {user_id}")
    return await UserService.update_user(db, user_id, user_update)

@router.delete(
    "/{user_id}",
    summary="Delete a user",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(role_required(["admin"]))] # Only 'admin' can delete users
)
async def delete_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a user from the system.
    Requires 'admin' role.
    """
    logger.info(f"Admin attempting to delete user with ID: {user_id}")
    await UserService.delete_user(db, user_id)
    return {"message": "User deleted successfully"}

# --- Role Endpoints ---
@router.post(
    "/roles/",
    response_model=RoleResponse,
    summary="Create a new role",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(role_required(["admin"]))] # Only 'admin' can create roles
)
async def create_role_endpoint(
    role: RoleCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new role in the system.
    Requires 'admin' role.
    """
    logger.info(f"Admin attempting to create role: {role.name}")
    return await RoleService.create_role(db, role)

@router.get(
    "/roles/",
    response_model=List[RoleResponse],
    summary="Get all roles",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(role_required(["admin", "process_manager"]))] # 'admin' or 'process_manager' can view roles
)
async def read_roles_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a list of all roles.
    Requires 'admin' or 'process_manager' role.
    """
    logger.info(f"Fetching all roles (skip={skip}, limit={limit})")
    return await RoleService.get_all_roles(db, skip=skip, limit=limit)