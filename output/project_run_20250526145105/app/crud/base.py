from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import select

# Define type variables for SQLAlchemy model and Pydantic schemas
ModelType = TypeVar("ModelType", bound=Any)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for CRUD operations.

    This class provides generic methods for interacting with a database table
    using SQLAlchemy, supporting common Create, Read, Update, and Delete operations.

    Args:
        model: A SQLAlchemy model class (e.g., `app.models.Customer`).
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model
        # Dynamically determine the primary key column name of the model.
        # This assumes a single primary key column for simplicity in CRUDBase.
        # For models with composite primary keys, this would require more complex logic.
        self.pk_column_name = next(iter(model.__table__.primary_key.columns)).name

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Retrieve a single record by its primary key.

        Args:
            db: The database session.
            id: The primary key value of the record to retrieve.

        Returns:
            The SQLAlchemy model instance if found, otherwise None.
        """
        # Access the primary key column dynamically using its name
        pk_column = getattr(self.model, self.pk_column_name)
        return db.execute(select(self.model).filter(pk_column == id)).scalar_one_or_none()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Retrieve multiple records with pagination.

        Args:
            db: The database session.
            skip: The number of records to skip (offset).
            limit: The maximum number of records to return.

        Returns:
            A list of SQLAlchemy model instances.
        """
        return db.execute(select(self.model).offset(skip).limit(limit)).scalars().all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record in the database.

        Args:
            db: The database session.
            obj_in: A Pydantic schema containing the data for the new record.

        Returns:
            The newly created SQLAlchemy model instance.
        """
        # Convert the Pydantic schema object to a dictionary, handling JSON-serializable types.
        obj_in_data = jsonable_encoder(obj_in)
        # Create a new SQLAlchemy model instance from the dictionary data.
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)  # Refresh the object to load any database-generated values (e.g., default timestamps).
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update an existing record in the database.

        Args:
            db: The database session.
            db_obj: The existing SQLAlchemy model instance to update.
            obj_in: A Pydantic schema or a dictionary containing the update data.
                    If a Pydantic schema, only fields that are explicitly set will be used for update.

        Returns:
            The updated SQLAlchemy model instance.
        """
        # Convert the existing database object to a dictionary for easy field iteration.
        obj_data = jsonable_encoder(db_obj)

        # Determine the source of update data.
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            # For Pydantic schema, use .dict(exclude_unset=True) to only get fields
            # that were provided in the input, ignoring default values or unset fields.
            update_data = obj_in.dict(exclude_unset=True)

        # Iterate over the fields of the existing object and apply updates.
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)  # Re-add the object to the session to mark it as dirty.
        db.commit()
        db.refresh(db_obj)  # Refresh to ensure the object reflects the latest state from the DB.
        return db_obj

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        Delete a record from the database by its primary key.

        Args:
            db: The database session.
            id: The primary key value of the record to delete.

        Returns:
            The deleted SQLAlchemy model instance if found and deleted, otherwise None.
        """
        pk_column = getattr(self.model, self.pk_column_name)
        # Retrieve the object first to ensure it exists and to return it after deletion.
        obj = db.execute(select(self.model).filter(pk_column == id)).scalar_one_or_none()
        if obj:
            db.delete(obj)
            db.commit()
        return obj