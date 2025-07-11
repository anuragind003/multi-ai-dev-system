from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from app.database import SessionLocal
from app.security import oauth2_scheme, decode_access_token
from app.services.user_service import UserService
from app.models import User
from app.utils.logger import get_logger

logger = get_logger(__name__)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    It ensures the session is closed after the request is processed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    """
    token_data = decode_access_token(token)
    
    user_service = UserService(db)
    user = user_service.get_user_by_username(username=token_data.username)
    
    if user is None:
        logger.warning(f"Authentication failed: User '{token_data.username}' not found in DB.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current authenticated and active user.
    """
    if not current_user.is_active:
        logger.warning(f"Authentication failed: User '{current_user.username}' is inactive.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user