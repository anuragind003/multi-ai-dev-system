from typing import TypeVar, Type, Generic, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect

from app.database import Base
from app.models import User, Role
from app.schemas import UserCreate, RoleCreate
from app.utils.logger import logger

# Define a type variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=Base) # Not strictly used for all CRUD, but good for consistency

class CRUDBase(Generic[ModelType]):
    """
    Base class for CRUD operations. Provides common methods for interacting with a database table.
    """
    def __init__(self, model: Type[ModelType]):
        """
        Initializes the CRUD operations with a specific SQLAlchemy model.
        """
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Retrieve a single record by its ID."""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieve multiple records with pagination."""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record from a Pydantic schema."""
        # Convert Pydantic schema to dictionary, excluding unset values
        obj_in_data = obj_in.model_dump(exclude_unset=True)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error during creation of {self.model.__name__}: {e}", exc_info=True)
            raise # Re-raise to be caught by service layer
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}", exc_info=True)
            raise

    def update(self, db: Session, db_obj: ModelType, obj_in: dict) -> ModelType:
        """Update an existing record with new data."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating {self.model.__name__} (ID: {db_obj.id}): {e}", exc_info=True)
            raise

    def remove(self, db: Session, id: int) -> Optional[ModelType]:
        """Delete a record by its ID."""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            try:
                db.commit()
                return obj
            except Exception as e:
                db.rollback()
                logger.error(f"Error removing {self.model.__name__} (ID: {id}): {e}", exc_info=True)
                raise
        return None

class CRUDUser(CRUDBase[User]):
    """
    CRUD operations specific to the User model.
    """
    def __init__(self, model: Type[User]):
        super().__init__(model)

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Retrieve a user by their email address."""
        return db.query(self.model).filter(self.model.email == email).first()

    def create_user(self, db: Session, user_in: UserCreate, role_id: int) -> User:
        """
        Create a new user with a hashed password and assigned role.
        This method assumes password hashing is done externally (e.g., in service layer).
        """
        db_user = User(
            email=user_in.email,
            hashed_password=user_in.password, # This should be the already hashed password
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            role_id=role_id,
            is_active=True
        )
        db.add(db_user)
        try:
            db.commit()
            db.refresh(db_user)
            return db_user
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Attempted to create duplicate user email: {user_in.email}")
            raise # Re-raise for service layer to handle specific exception
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create user {user_in.email}: {e}", exc_info=True)
            raise

class CRUDRole(CRUDBase[Role]):
    """
    CRUD operations specific to the Role model.
    """
    def __init__(self, model: Type[Role]):
        super().__init__(model)

    def get_by_name(self, db: Session, name: str) -> Optional[Role]:
        """Retrieve a role by its name."""
        return db.query(self.model).filter(self.model.name == name).first()

    def create_role(self, db: Session, role_in: RoleCreate) -> Role:
        """Create a new role."""
        db_role = Role(name=role_in.name)
        db.add(db_role)
        try:
            db.commit()
            db.refresh(db_role)
            return db_role
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Attempted to create duplicate role name: {role_in.name}")
            raise # Re-raise for service layer to handle specific exception
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create role {role_in.name}: {e}", exc_info=True)
            raise