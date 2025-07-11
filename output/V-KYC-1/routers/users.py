from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import UserCreate, UserUpdate, UserResponse, LoginRequest, Token
from services import UserService
from middleware.security import get_current_user, create_access_token, require_role
from models import User, UserRole
from utils.exceptions import UnauthorizedException, ForbiddenException, NotFoundException, ConflictException
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/auth/login", response_model=Token, summary="Authenticate User and Get Token")
async def login_for_access_token(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user with username and password, returning an access token upon success.
    """
    user_service = UserService(db)
    user = await user_service.authenticate_user(login_data)
    if not user:
        raise UnauthorizedException(detail="Incorrect username or password.")
    
    access_token = create_access_token(
        data={"sub": user.username, "roles": [user.role.value]}
    )
    logger.info(f"User '{user.username}' successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post(
    "/users/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a New User (Admin/Manager Only)",
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))]
)
async def create_user(
    user_create: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new user account.
    - **Admin** can create users with any role.
    - **Manager** can create users with `user` role only.
    - Requires authentication.
    """
    user_service = UserService(db)
    logger.info(f"User {current_user.username} attempting to create user {user_create.username}.")
    new_user = await user_service.create_user(user_create, current_user)
    return UserResponse.model_validate(new_user)

@router.get(
    "/users/",
    response_model=List[UserResponse],
    summary="Get All Users (Admin/Manager Only)",
    dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))]
)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a list of all user accounts with pagination.
    - Requires **Admin** or **Manager** role.
    """
    user_service = UserService(db)
    logger.info(f"User {current_user.username} requesting all users.")
    users = await user_service.get_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(user) for user in users]

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get User by ID (Admin/Manager/Self)",
    dependencies=[Depends(get_current_user)]
)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a single user account by its ID.
    - **Admin** can retrieve any user.
    - **Manager** can retrieve any user.
    - **User** can only retrieve their own profile.
    """
    user_service = UserService(db)
    logger.info(f"User {current_user.username} requesting user ID {user_id}.")
    
    # Authorization check: A user can only view their own profile unless they are Admin/Manager
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise ForbiddenException(detail="You are not authorized to view this user's profile.")
    
    user = await user_service.get_user(user_id)
    return UserResponse.model_validate(user)

@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update User by ID (Admin/Manager/Self)",
    dependencies=[Depends(get_current_user)]
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates an existing user account.
    - **Admin** can update any user.
    - **Manager** can update users with `user` role.
    - **User** can only update their own profile (username, email, password, is_active).
    - Role changes are restricted to Admins.
    """
    user_service = UserService(db)
    logger.info(f"User {current_user.username} attempting to update user ID {user_id}.")
    updated_user = await user_service.update_user(user_id, user_update, current_user)
    return UserResponse.model_validate(updated_user)

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User by ID (Admin Only)",
    dependencies=[Depends(require_role([UserRole.ADMIN]))]
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a user account by its ID.
    - Requires **Admin** role.
    - A user cannot delete their own account.
    """
    user_service = UserService(db)
    logger.info(f"User {current_user.username} attempting to delete user ID {user_id}.")
    
    deleted = await user_service.delete_user(user_id, current_user)
    if not deleted:
        raise NotFoundException(detail=f"User with ID {user_id} not found.")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)