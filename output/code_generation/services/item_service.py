import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import Item
from schemas import ItemCreate
from core.exceptions import NotFoundException, BadRequestException

logger = logging.getLogger(__name__)

class ItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """Fetches an item by its ID."""
        result = await self.db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            logger.warning(f"Item with ID {item_id} not found.")
        return item

    async def create_item(self, item_in: ItemCreate, owner_id: int) -> Item:
        """Creates a new item for a given owner."""
        db_item = Item(
            title=item_in.title,
            description=item_in.description,
            owner_id=owner_id
        )
        self.db.add(db_item)
        await self.db.commit()
        await self.db.refresh(db_item)
        logger.info(f"Item '{db_item.title}' created successfully by user ID {owner_id}.")
        return db_item

    async def get_all_items(self, skip: int = 0, limit: int = 100) -> List[Item]:
        """Fetches all items with pagination."""
        result = await self.db.execute(select(Item).offset(skip).limit(limit))
        items = result.scalars().all()
        logger.info(f"Fetched {len(items)} items.")
        return list(items)

    async def get_items_by_owner(self, owner_id: int, skip: int = 0, limit: int = 100) -> List[Item]:
        """Fetches items owned by a specific user with pagination."""
        result = await self.db.execute(
            select(Item).where(Item.owner_id == owner_id).offset(skip).limit(limit)
        )
        items = result.scalars().all()
        logger.info(f"Fetched {len(items)} items for owner ID {owner_id}.")
        return list(items)

    async def update_item(self, item_id: int, item_in: ItemCreate, current_user_id: int) -> Item:
        """
        Updates an existing item.
        Raises NotFoundException if item does not exist.
        Raises ForbiddenException if current user is not the owner.
        """
        db_item = await self.get_item_by_id(item_id)
        if not db_item:
            raise NotFoundException(detail=f"Item with ID {item_id} not found.")
        
        # Ensure only the owner can update their item
        if db_item.owner_id != current_user_id:
            raise BadRequestException(detail="You are not authorized to update this item.")

        for field, value in item_in.model_dump(exclude_unset=True).items():
            setattr(db_item, field, value)

        await self.db.commit()
        await self.db.refresh(db_item)
        logger.info(f"Item with ID {item_id} updated successfully by user ID {current_user_id}.")
        return db_item

    async def delete_item(self, item_id: int, current_user_id: int) -> bool:
        """
        Deletes an item by its ID.
        Returns True if deleted, False if not found.
        Raises ForbiddenException if current user is not the owner.
        """
        db_item = await self.get_item_by_id(item_id)
        if not db_item:
            logger.warning(f"Attempted to delete non-existent item with ID {item_id}.")
            return False
        
        # Ensure only the owner can delete their item
        if db_item.owner_id != current_user_id:
            raise BadRequestException(detail="You are not authorized to delete this item.")

        await self.db.delete(db_item)
        await self.db.commit()
        logger.info(f"Item with ID {item_id} deleted successfully by user ID {current_user_id}.")
        return True