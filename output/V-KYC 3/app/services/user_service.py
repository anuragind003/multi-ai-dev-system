from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User, Role
from app.schemas import UserCreate, UserUpdate
from app.security import get_password_hash
from app.exceptions import NotFoundException, ConflictException, InvalidInputException
from app.logger import logger

class UserService:
    """
    Service layer for managing user-related business logic.
    Handles CRUD operations for users, including password hashing and role assignment.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.info(f"User with ID {user_id} not found.")
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email address."""
        return self.db.query(User).filter(User.email == email).first()

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieves a list of all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def create_user(self, user_data: UserCreate) -> User:
        """
        Creates a new user.
        Hashes the password and assigns the specified role.
        Raises ConflictException if email already exists.
        Raises NotFoundException if the specified role_id does not exist.
        """
        if self.get_user_by_email(user_data.email):
            logger.warning(f"Attempted to create user with existing email: {user_data.email}")
            raise ConflictException(detail=f"User with email '{user_data.email}' already exists.")

        role = self.db.query(Role).filter(Role.id == user_data.role_id).first()
        if not role:
            logger.warning(f"Attempted to create user with non-existent role ID: {user_data.role_id}")
            raise NotFoundException(detail=f"Role with ID {user_data.role_id} not found.")

        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_active=user_data.is_active,
            role_id=user_data.role_id
        )
        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            logger.info(f"User '{db_user.email}' created successfully with role '{role.name}'.")
            return db_user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during user creation: {e}")
            raise ConflictException(detail=f"A database conflict occurred, possibly duplicate email: {user_data.email}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user {user_data.email}: {e}")
            raise InvalidInputException(detail=f"Failed to create user due to invalid input or server error: {e}")


    def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Updates an existing user's details.
        Raises NotFoundException if the user does not exist.
        Raises ConflictException if attempting to change email to an already existing one.
        Raises NotFoundException if the specified role_id does not exist.
        """
        db_user = self.get_user_by_id(user_id) # This will raise NotFoundException if user doesn't exist

        if user_data.email and user_data.email != db_user.email:
            if self.get_user_by_email(user_data.email):
                logger.warning(f"Attempted to update user {user_id} to existing email: {user_data.email}")
                raise ConflictException(detail=f"Email '{user_data.email}' is already taken by another user.")

        if user_data.role_id is not None and user_data.role_id != db_user.role_id:
            role = self.db.query(Role).filter(Role.id == user_data.role_id).first()
            if not role:
                logger.warning(f"Attempted to update user {user_id} with non-existent role ID: {user_data.role_id}")
                raise NotFoundException(detail=f"Role with ID {user_data.role_id} not found.")
            db_user.role_id = user_data.role_id

        update_data = user_data.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        # Apply updates, excluding 'password' as it's handled separately
        for key, value in update_data.items():
            if key != "password": # Ensure password field itself is not directly assigned
                setattr(db_user, key, value)

        try:
            self.db.commit()
            self.db.refresh(db_user)
            logger.info(f"User '{db_user.email}' (ID: {user_id}) updated successfully.")
            return db_user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during user update for ID {user_id}: {e}")
            raise ConflictException(detail=f"A database conflict occurred during update, possibly duplicate email.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise InvalidInputException(detail=f"Failed to update user due to invalid input or server error: {e}")

    def delete_user(self, user_id: int) -> None:
        """
        Deletes a user by their ID.
        Raises NotFoundException if the user does not exist.
        """
        db_user = self.get_user_by_id(user_id) # This will raise NotFoundException if user doesn't exist
        
        try:
            self.db.delete(db_user)
            self.db.commit()
            logger.info(f"User '{db_user.email}' (ID: {user_id}) deleted successfully.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise InvalidInputException(detail=f"Failed to delete user due to server error: {e}")