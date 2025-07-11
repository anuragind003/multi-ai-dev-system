from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db_session
from crud.user_crud import UserCRUD
from crud.test_crud import TestCRUD
from services.auth_service import AuthService
from services.test_service import TestService
from models import User
from core.security import oauth2_scheme, verify_token
from core.exceptions import UnauthorizedException, ForbiddenException

logger = logging.getLogger(__name__)

# --- Database Session Dependency ---
def get_db() -> AsyncSession:
    """Provides an asynchronous database session."""
    return Depends(get_db_session)

# --- CRUD Dependencies ---
def get_user_crud(db: AsyncSession = get_db()) -> UserCRUD:
    """Provides a UserCRUD instance."""
    return UserCRUD(db)

def get_test_crud(db: AsyncSession = get_db()) -> TestCRUD:
    """Provides a TestCRUD instance."""
    return TestCRUD(db)

# --- Service Dependencies ---
def get_auth_service(user_crud: UserCRUD = Depends(get_user_crud)) -> AuthService:
    """Provides an AuthService instance."""
    return AuthService(user_crud)

def get_test_service(
    test_crud: TestCRUD = Depends(get_test_crud),
    user_crud: UserCRUD = Depends(get_user_crud)
) -> TestService:
    """Provides a TestService instance."""
    return TestService(test_crud, user_crud)

# --- Current User Dependencies ---
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Retrieves the current authenticated user based on the provided JWT token.
    Raises UnauthorizedException if the token is invalid or user is not found/inactive.
    """
    try:
        user_response = await auth_service.get_current_user(token)
        # Convert UserResponse to User model instance for consistency in downstream dependencies
        # This is a simple conversion, for complex scenarios, consider a dedicated mapper or just use UserResponse
        user = User(
            id=user_response.id,
            username=user_response.username,
            email=user_response.email,
            is_active=user_response.is_active,
            role=user_response.role,
            # hashed_password is not in UserResponse, but not needed for authorization checks
            # created_at and updated_at are not strictly needed for auth, but can be set if desired
        )
        return user
    except UnauthorizedException as e:
        logger.warning(f"Authentication failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication.",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensures the current user is active."""
    if not current_user.is_active:
        logger.warning(f"Inactive user '{current_user.username}' attempted access.")
        raise ForbiddenException("Inactive user.")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Ensures the current user has the 'admin' role."""
    if current_user.role != "admin":
        logger.warning(f"User '{current_user.username}' (role: {current_user.role}) attempted admin access.")
        raise ForbiddenException("Not authorized. Requires admin role.")
    return current_user

async def get_current_qa_engineer_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Ensures the current user has the 'qa_engineer' or 'admin' role."""
    if current_user.role not in ["qa_engineer", "admin"]:
        logger.warning(f"User '{current_user.username}' (role: {current_user.role}) attempted QA Engineer access.")
        raise ForbiddenException("Not authorized. Requires QA Engineer or Admin role.")
    return current_user