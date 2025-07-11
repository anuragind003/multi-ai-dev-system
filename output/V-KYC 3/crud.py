from typing import TypeVar, Type, Any, List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Base, User, Role
from schemas import UserCreate, UserUpdate, RoleCreate
from utils.logger import logger

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=Base)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=Base)

class CRUDBase:
    """
    Base class for CRUD operations.
    Provides generic methods for creating, reading, updating, and deleting records.
    """
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Any) -> Optional[ModelType]:
        """Retrieve a single record by its ID."""
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieve multiple records with pagination."""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        logger.info(f"Created new {self.model.__name__} with ID: {db_obj.id}")
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: UpdateSchemaType | Dict[str, Any]) -> ModelType:
        """Update an existing record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True) # Only update fields that are set

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        logger.info(f"Updated {self.model.__name__} with ID: {db_obj.id}")
        return db_obj

    async def delete(self, id: Any) -> Optional[ModelType]:
        """Delete a record by its ID."""
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted {self.model.__name__} with ID: {id}")
            return obj
        return None

class CRUDUser(CRUDBase):
    """
    CRUD operations specific to the User model.
    """
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by their email address, eagerly loading their role."""
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).filter(User.email == email)
        )
        return result.scalars().first()

    async def create_user(self, obj_in: UserCreate, role_id: int) -> User:
        """Create a new user with a hashed password and assigned role."""
        db_obj = User(
            email=obj_in.email,
            hashed_password=obj_in.password, # Password should be hashed before passing here
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            is_active=obj_in.is_active,
            role_id=role_id
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        logger.info(f"Created user: {db_obj.email} with role_id: {role_id}")
        return db_obj

    async def get_all_users_with_roles(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieve all users, eagerly loading their roles."""
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).offset(skip).limit(limit)
        )
        return result.scalars().all()

class CRUDRole(CRUDBase):
    """
    CRUD operations specific to the Role model.
    """
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_name(self, name: str) -> Optional[Role]:
        """Retrieve a role by its name."""
        result = await self.db.execute(select(Role).filter(Role.name == name))
        return result.scalars().first()

    async def create_role(self, obj_in: RoleCreate) -> Role:
        """Create a new role."""
        db_obj = Role(name=obj_in.name)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        logger.info(f"Created role: {db_obj.name}")
        return db_obj