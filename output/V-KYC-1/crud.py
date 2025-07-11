from typing import TypeVar, Type, Generic, List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel

from database import Base
from utils.exceptions import DuplicateEntryException, NotFoundException, DatabaseOperationException
from utils.logger import logger
from models import User, RecordingMetadata, UserRole, RecordingStatus

# Define a type variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)
# Define a type variable for Pydantic schemas
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for CRUD operations on SQLAlchemy models.
    Provides generic methods for common database interactions.
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Retrieve a single record by its ID."""
        try:
            result = await db.execute(select(self.model).filter(self.model.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching {self.model.__name__} by ID {id}: {e}")
            raise DatabaseOperationException(f"Failed to retrieve {self.model.__name__}.")

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Retrieve multiple records with optional filtering, skipping, and limiting."""
        try:
            query = select(self.model)
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        # Basic filtering for exact match or partial match for strings
                        if isinstance(value, str):
                            query = query.filter(getattr(self.model, field).ilike(f"%{value}%"))
                        else:
                            query = query.filter(getattr(self.model, field) == value)
            
            query = query.offset(skip).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching multiple {self.model.__name__}: {e}")
            raise DatabaseOperationException(f"Failed to retrieve multiple {self.model.__name__}.")

    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record in the database."""
        try:
            db_obj = self.model(**obj_in.model_dump())
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await db.rollback()
            logger.warning(f"Integrity error creating {self.model.__name__}: {e.orig}")
            raise DuplicateEntryException(f"A record with similar unique identifier already exists for {self.model.__name__}.")
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            raise DatabaseOperationException(f"Failed to create {self.model.__name__}.")

    async def update(
        self, db: AsyncSession, db_obj: ModelType, obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """Update an existing record in the database."""
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True) # Only update fields that are set

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            await db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await db.rollback()
            logger.warning(f"Integrity error updating {self.model.__name__} (ID: {db_obj.id}): {e.orig}")
            raise DuplicateEntryException(f"Update failed: A record with similar unique identifier already exists for {self.model.__name__}.")
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error updating {self.model.__name__} (ID: {db_obj.id}): {e}")
            raise DatabaseOperationException(f"Failed to update {self.model.__name__}.")

    async def delete(self, db: AsyncSession, id: int) -> bool:
        """Delete a record by its ID."""
        try:
            result = await db.execute(select(self.model).filter(self.model.id == id))
            db_obj = result.scalar_one_or_none()
            if db_obj:
                await db.delete(db_obj)
                await db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error deleting {self.model.__name__} (ID: {id}): {e}")
            raise DatabaseOperationException(f"Failed to delete {self.model.__name__}.")

class CRUDUser(CRUDBase[User, BaseModel, BaseModel]):
    """CRUD operations for User model."""
    def __init__(self):
        super().__init__(User)

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Retrieve a user by their username."""
        try:
            result = await db.execute(select(self.model).filter(self.model.username == username))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching User by username {username}: {e}")
            raise DatabaseOperationException("Failed to retrieve user by username.")

class CRUDRecordingMetadata(CRUDBase[RecordingMetadata, BaseModel, BaseModel]):
    """CRUD operations for RecordingMetadata model."""
    def __init__(self):
        super().__init__(RecordingMetadata)

    async def get_by_lan_id(self, db: AsyncSession, lan_id: str) -> Optional[RecordingMetadata]:
        """Retrieve recording metadata by LAN ID."""
        try:
            result = await db.execute(select(self.model).filter(self.model.lan_id == lan_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching RecordingMetadata by LAN ID {lan_id}: {e}")
            raise DatabaseOperationException("Failed to retrieve recording metadata by LAN ID.")

    async def get_filtered_recordings(
        self,
        db: AsyncSession,
        lan_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        status: Optional[RecordingStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[RecordingMetadata]:
        """
        Retrieve recording metadata based on various filters.
        """
        try:
            query = select(self.model)

            if lan_id:
                query = query.filter(self.model.lan_id.ilike(f"%{lan_id}%"))
            if customer_name:
                query = query.filter(self.model.customer_name.ilike(f"%{customer_name}%"))
            if status:
                query = query.filter(self.model.status == status)
            if start_date:
                query = query.filter(self.model.recording_date >= start_date)
            if end_date:
                query = query.filter(self.model.recording_date <= end_date)

            query = query.offset(skip).limit(limit).order_by(self.model.recording_date.desc())

            result = await db.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching filtered recordings: {e}")
            raise DatabaseOperationException("Failed to retrieve filtered recording metadata.")

# Instantiate CRUD objects for direct use
user_crud = CRUDUser()
recording_crud = CRUDRecordingMetadata()