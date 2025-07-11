from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.security import verify_token
from core.exceptions import CredentialException, ForbiddenException
from db.database import get_db
from db.models import User
from schemas.user_schemas import TokenData
from services.user_service import UserService
from core.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from a JWT token.
    Raises CredentialException if token is invalid or user not found.
    """
    token_data = verify_token(token)
    email = token_data.get("sub")
    if email is None:
        raise CredentialException()

    user_service = UserService(db)
    user = user_service.get_user_by_email(email=email)
    if user is None:
        raise CredentialException()
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active authenticated user.
    Raises CredentialException if user is inactive.
    """
    if not current_user.is_active:
        raise CredentialException(detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active authenticated superuser.
    Raises ForbiddenException if user is not a superuser.
    """
    if not current_user.is_superuser or not current_user.is_active:
        raise ForbiddenException(detail="The user doesn't have enough privileges")
    return current_user