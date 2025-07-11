from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from config import settings
from schemas import TokenData
from utils.logger import get_logger
from utils.exceptions import UnauthorizedException

logger = get_logger(__name__)

# OAuth2PasswordBearer for handling token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency to get the current authenticated user from a JWT token.
    Raises HTTPException if token is invalid or expired.
    """
    credentials_exception = UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT payload missing 'sub' (username).")
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}", exc_info=True)
        raise credentials_exception
    
    # In a real application, you might fetch the user from the database here
    # to ensure they still exist and are active.
    # For this example, we assume the username from the token is sufficient.
    
    logger.debug(f"User '{token_data.username}' authenticated via JWT.")
    return token_data.username