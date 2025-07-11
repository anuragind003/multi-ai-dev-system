from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from repositories import UserRepository
from schemas import UserCreate, UserUpdate, LoginRequest
from models import User, UserRole
from utils.exceptions import NotFoundException, ConflictException, UnauthorizedException, ForbiddenException, ValidationException
from middleware.security import get_password_hash, verify_password
from utils.logger import get_logger

logger = get_logger(__name__)

class UserService:
    """
    Service layer for User management.
    Contains business logic, interacts with the UserRepository.
    """
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)

    async def create_user(self, user_data: UserCreate, current_user: User) -> User:
        """
        Creates a new user.
        Requires admin privileges to set roles other than 'user'.
        """
        if user_data.role != UserRole.USER and current_user.role != UserRole.ADMIN:
            raise ForbiddenException(detail="Only administrators can create users with elevated roles.")
        
        # Hash the password before sending to repository
        hashed_password = get_password_hash(user_data.password)
        user_data.password = hashed_password # Update the Pydantic model with hashed password

        logger.info(f"Attempting to create user: {user_data.username}")
        return await self.user_repo.create(user_data)

    async def get_user(self, user_id: int) -> User:
        """
        Retrieves a single user by ID.
        Raises NotFoundException if user does not exist.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        logger.debug(f"Retrieved user: {user.username}")
        return user

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Retrieves a list of users with pagination.
        """
        logger.debug(f"Retrieving users (skip={skip}, limit={limit})")
        return await self.user_repo.get_all(skip=skip, limit=limit)

    async def update_user(self, user_id: int, user_data: UserUpdate, current_user: User) -> User:
        """
        Updates an existing user.
        Admins can update any user. Managers can update users with 'user' role.
        Users can only update their own profile (username, email, password, is_active).
        """
        existing_user = await self.user_repo.get_by_id(user_id)
        if not existing_user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")

        # Authorization checks
        if current_user.id != user_id: # Not updating self
            if current_user.role == UserRole.USER:
                raise ForbiddenException(detail="You are not authorized to update other user accounts.")
            if current_user.role == UserRole.MANAGER and existing_user.role != UserRole.USER:
                raise ForbiddenException(detail="Managers can only update users with 'user' role.")
            if user_data.role is not None and user_data.role != existing_user.role and current_user.role != UserRole.ADMIN:
                raise ForbiddenException(detail="Only administrators can change user roles.")
            if user_data.is_active is not None and user_data.is_active != existing_user.is_active and current_user.role != UserRole.ADMIN:
                raise ForbiddenException(detail="Only administrators can change user active status.")
        
        # If updating self, restrict role changes
        if current_user.id == user_id and user_data.role is not None and user_data.role != existing_user.role:
            raise ForbiddenException(detail="You cannot change your own role.")
        
        # Hash new password if provided
        if user_data.password:
            user_data.password = get_password_hash(user_data.password)
        
        logger.info(f"Attempting to update user ID: {user_id}")
        return await self.user_repo.update(user_id, user_data)

    async def delete_user(self, user_id: int, current_user: User) -> bool:
        """
        Deletes a user.
        Only administrators can delete users.
        A user cannot delete themselves.
        """
        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException(detail="Only administrators can delete user accounts.")
        
        if current_user.id == user_id:
            raise ForbiddenException(detail="You cannot delete your own account.")

        existing_user = await self.user_repo.get_by_id(user_id)
        if not existing_user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        
        logger.info(f"Attempting to delete user ID: {user_id}")
        return await self.user_repo.delete(user_id)

    async def authenticate_user(self, login_data: LoginRequest) -> Optional[User]:
        """
        Authenticates a user based on username and password.
        Returns the User object if authentication is successful, None otherwise.
        """
        user = await self.user_repo.get_by_username(login_data.username)
        if not user:
            logger.warning(f"Authentication failed for username '{login_data.username}': User not found.")
            return None
        
        if not user.is_active:
            logger.warning(f"Authentication failed for username '{login_data.username}': User is inactive.")
            return None

        if not verify_password(login_data.password, user.hashed_password):
            logger.warning(f"Authentication failed for username '{login_data.username}': Invalid password.")
            return None
        
        logger.info(f"User '{user.username}' authenticated successfully.")
        return user