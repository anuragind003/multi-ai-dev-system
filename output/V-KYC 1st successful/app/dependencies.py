from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from app.core.security import get_current_user, require_roles
from app.core.security import UserInDB # Import UserInDB for type hinting

# Centralized dependencies for easier management and consistency

# Dependency to get an asynchronous database session
DBSession = Annotated[AsyncSession, Depends(get_db_session)]

# Dependency to get the current authenticated user
CurrentUser = Annotated[UserInDB, Depends(get_current_user)]

# Dependency for role-based access control (example usage)
# AdminUser = Annotated[UserInDB, Depends(require_roles(["admin"]))]
# TeamLeadUser = Annotated[UserInDB, Depends(require_roles(["team_lead"]))]
# RegularUser = Annotated[UserInDB, Depends(require_roles(["user"]))]