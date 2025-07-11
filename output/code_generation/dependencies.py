from typing import Annotated
from fastapi import Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from security import oauth2_scheme, decode_access_token
from exceptions import UnauthorizedException, ForbiddenException
from models import User, UserRole
from sqlalchemy.future import select
from schemas import TokenData
import logging

logger = logging.getLogger("security_testing_api")

# Dependency for database session
DBSession = Annotated[AsyncSession, Depends(get_db_session)]

async def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DBSession
) -> User:
    """
    Dependency to get the current authenticated user.
    It decodes the JWT token, fetches the user from the database,
    and checks if the user has the required scopes.
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise UnauthorizedException(headers={"WWW-Authenticate": authenticate_value})
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except UnauthorizedException as e:
        logger.warning(f"Authentication failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during token processing: {e}")
        raise UnauthorizedException(headers={"WWW-Authenticate": authenticate_value})

    # Fetch user from DB
    result = await db.execute(select(User).where(User.username == token_data.username))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"User '{token_data.username}' not found in DB after token validation.")
        raise UnauthorizedException(detail="User not found", headers={"WWW-Authenticate": authenticate_value})

    if not user.is_active:
        logger.warning(f"Inactive user '{user.username}' attempted access.")
        raise ForbiddenException(detail="Inactive user")

    # Check scopes/roles
    required_scopes = set(security_scopes.scopes)
    user_role_scope = user.role.value # e.g., "admin", "tester", "viewer"

    # If 'admin' scope is required, only admin can pass.
    # If 'tester' scope is required, admin or tester can pass.
    # If 'viewer' scope is required, admin, tester, or viewer can pass.
    # This implies a hierarchy: admin > tester > viewer
    has_permission = False
    if "admin" in required_scopes and user_role_scope == UserRole.ADMIN:
        has_permission = True
    elif "tester" in required_scopes and (user_role_scope == UserRole.ADMIN or user_role_scope == UserRole.TESTER):
        has_permission = True
    elif "viewer" in required_scopes and (user_role_scope == UserRole.ADMIN or user_role_scope == UserRole.TESTER or user_role_scope == UserRole.VIEWER):
        has_permission = True
    elif not required_scopes: # No specific scopes required, just authenticated
        has_permission = True

    if not has_permission:
        logger.warning(f"User '{user.username}' with role '{user.role}' lacks required scopes: {required_scopes}")
        raise ForbiddenException(detail="Not enough permissions")

    return user

# Specific role dependencies for convenience
def get_current_admin_user(current_user: Annotated[User, Security(get_current_user, scopes=["admin"])]):
    return current_user

def get_current_tester_or_admin_user(current_user: Annotated[User, Security(get_current_user, scopes=["tester"])]):
    return current_user

def get_current_viewer_or_above_user(current_user: Annotated[User, Security(get_current_user, scopes=["viewer"])]):
    return current_user