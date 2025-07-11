from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db_session
from repositories.user_repository import UserRepository
from services.user_service import UserService

logger = logging.getLogger(__name__)

async def get_user_repository(
    db_session: AsyncSession = Depends(get_db_session)
) -> AsyncGenerator[UserRepository, None]:
    """
    Dependency that provides a UserRepository instance.
    Injects an AsyncSession into the repository.
    """
    logger.debug("Providing UserRepository dependency.")
    yield UserRepository(db_session)

async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository)
) -> AsyncGenerator[UserService, None]:
    """
    Dependency that provides a UserService instance.
    Injects a UserRepository into the service.
    """
    logger.debug("Providing UserService dependency.")
    yield UserService(user_repo)

# You can add more dependencies here as your application grows,
# e.g., for other repositories, services, or external clients.