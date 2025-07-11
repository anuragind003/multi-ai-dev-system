from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models import User, Role, Permission
from schemas import UserCreate, UserUpdate, RoleCreate, PermissionCreate
from auth_utils import get_password_hash
from core.exceptions import NotFoundException, ConflictException, CustomHTTPException
from core.logging_config import setup_logging

logger = setup_logging()

class UserService:
    """
    Service layer for User, Role, and Permission management.
    Handles business logic and interacts with the database.
    """
    def __init__(self, db: Session):
        self.db = db

    # --- User Operations ---
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email address."""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieves a list of users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def create_user(self, user_in: UserCreate) -> User:
        """
        Creates a new user.
        Raises ConflictException if email already exists.
        """
        if self.get_user_by_email(user_in.email):
            logger.warning(f"Attempted to create user with existing email: {user_in.email}")
            raise ConflictException(detail=f"User with email '{user_in.email}' already exists.")

        hashed_password = get_password_hash(user_in.password)
        db_user = User(email=user_in.email, hashed_password=hashed_password, is_active=user_in.is_active)
        
        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            logger.info(f"User created: {db_user.email}")
            return db_user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during user creation: {e}")
            raise ConflictException(detail="A user with this email already exists.") from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise CustomHTTPException(status_code=500, detail="Failed to create user due to an unexpected error.") from e

    def update_user(self, user_id: int, user_in: UserUpdate) -> User:
        """
        Updates an existing user's information.
        Raises NotFoundException if user does not exist.
        Raises ConflictException if new email already exists for another user.
        """
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            logger.warning(f"Attempted to update non-existent user with ID: {user_id}")
            raise NotFoundException(detail=f"User with ID {user_id} not found.")

        if user_in.email and user_in.email != db_user.email:
            existing_user = self.get_user_by_email(user_in.email)
            if existing_user and existing_user.id != user_id:
                logger.warning(f"Attempted to update user {user_id} with email {user_in.email} which is already taken by user {existing_user.id}")
                raise ConflictException(detail=f"Email '{user_in.email}' is already taken by another user.")

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        # Handle role updates
        if "role_ids" in update_data and update_data["role_ids"] is not None:
            new_roles = self.db.query(Role).filter(Role.id.in_(update_data.pop("role_ids"))).all()
            if len(new_roles) != len(user_in.role_ids):
                logger.warning(f"Some role IDs provided for user {user_id} were not found.")
                # Optionally raise an error or just assign existing roles
            db_user.roles = new_roles
        
        for key, value in update_data.items():
            setattr(db_user, key, value)

        try:
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            logger.info(f"User updated: {db_user.email} (ID: {db_user.id})")
            return db_user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise CustomHTTPException(status_code=500, detail="Failed to update user due to an unexpected error.") from e

    def delete_user(self, user_id: int) -> bool:
        """
        Deletes a user by their ID.
        Raises NotFoundException if user does not exist.
        """
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            logger.warning(f"Attempted to delete non-existent user with ID: {user_id}")
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        
        try:
            self.db.delete(db_user)
            self.db.commit()
            logger.info(f"User deleted: {db_user.email} (ID: {db_user.id})")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise CustomHTTPException(status_code=500, detail="Failed to delete user due to an unexpected error.") from e

    # --- Role Operations ---
    def get_role_by_name(self, name: str) -> Optional[Role]:
        """Retrieves a role by its name."""
        return self.db.query(Role).filter(Role.name == name).first()

    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """Retrieves a role by its ID."""
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_roles(self, skip: int = 0, limit: int = 100) -> List[Role]:
        """Retrieves a list of roles with pagination."""
        return self.db.query(Role).offset(skip).limit(limit).all()

    def create_role(self, role_in: RoleCreate) -> Role:
        """
        Creates a new role.
        Raises ConflictException if role name already exists.
        """
        if self.get_role_by_name(role_in.name):
            logger.warning(f"Attempted to create role with existing name: {role_in.name}")
            raise ConflictException(detail=f"Role with name '{role_in.name}' already exists.")
        
        db_role = Role(name=role_in.name, description=role_in.description)

        if role_in.permission_ids:
            permissions = self.db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
            if len(permissions) != len(role_in.permission_ids):
                logger.warning(f"Some permission IDs provided for role '{role_in.name}' were not found.")
            db_role.permissions = permissions
        
        try:
            self.db.add(db_role)
            self.db.commit()
            self.db.refresh(db_role)
            logger.info(f"Role created: {db_role.name}")
            return db_role
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during role creation: {e}")
            raise ConflictException(detail="A role with this name already exists.") from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating role: {e}")
            raise CustomHTTPException(status_code=500, detail="Failed to create role due to an unexpected error.") from e

    def assign_role_to_user(self, user_id: int, role_id: int) -> User:
        """
        Assigns a role to a user.
        Raises NotFoundException if user or role does not exist.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        
        role = self.get_role_by_id(role_id)
        if not role:
            raise NotFoundException(detail=f"Role with ID {role_id} not found.")
        
        if role not in user.roles:
            user.roles.append(role)
            try:
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"Role '{role.name}' assigned to user '{user.email}'.")
                return user
            except Exception as e:
                self.db.rollback()
                logger.error(f"Error assigning role {role_id} to user {user_id}: {e}")
                raise CustomHTTPException(status_code=500, detail="Failed to assign role due to an unexpected error.") from e
        else:
            logger.info(f"User '{user.email}' already has role '{role.name}'. No change made.")
            return user

    def remove_role_from_user(self, user_id: int, role_id: int) -> User:
        """
        Removes a role from a user.
        Raises NotFoundException if user or role does not exist.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        
        role = self.get_role_by_id(role_id)
        if not role:
            raise NotFoundException(detail=f"Role with ID {role_id} not found.")
        
        if role in user.roles:
            user.roles.remove(role)
            try:
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"Role '{role.name}' removed from user '{user.email}'.")
                return user
            except Exception as e:
                self.db.rollback()
                logger.error(f"Error removing role {role_id} from user {user_id}: {e}")
                raise CustomHTTPException(status_code=500, detail="Failed to remove role due to an unexpected error.") from e
        else:
            logger.info(f"User '{user.email}' does not have role '{role.name}'. No change made.")
            return user

    # --- Permission Operations ---
    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Retrieves a permission by its name."""
        return self.db.query(Permission).filter(Permission.name == name).first()

    def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """Retrieves a permission by its ID."""
        return self.db.query(Permission).filter(Permission.id == permission_id).first()

    def get_permissions(self, skip: int = 0, limit: int = 100) -> List[Permission]:
        """Retrieves a list of permissions with pagination."""
        return self.db.query(Permission).offset(skip).limit(limit).all()

    def create_permission(self, permission_in: PermissionCreate) -> Permission:
        """
        Creates a new permission.
        Raises ConflictException if permission name already exists.
        """
        if self.get_permission_by_name(permission_in.name):
            logger.warning(f"Attempted to create permission with existing name: {permission_in.name}")
            raise ConflictException(detail=f"Permission with name '{permission_in.name}' already exists.")
        
        db_permission = Permission(name=permission_in.name, description=permission_in.description)
        
        try:
            self.db.add(db_permission)
            self.db.commit()
            self.db.refresh(db_permission)
            logger.info(f"Permission created: {db_permission.name}")
            return db_permission
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during permission creation: {e}")
            raise ConflictException(detail="A permission with this name already exists.") from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating permission: {e}")
            raise CustomHTTPException(status_code=500, detail="Failed to create permission due to an unexpected error.") from e

# Dependency to inject UserService
def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)