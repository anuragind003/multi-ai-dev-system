from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import UnauthorizedException
from app.core.logging_config import logger
from app.schemas.common import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

async def get_current_user_token(token: Annotated[str, Depends(oauth2_scheme)]) -> TokenData:
    """
    Dependency to decode and validate JWT token.
    Returns TokenData containing username and scopes.
    """
    credentials_exception = UnauthorizedException(
        detail="Could not validate credentials",
        error_code="INVALID_CREDENTIALS"
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        scopes: list[str] = payload.get("scopes", [])
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, scopes=scopes)
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise credentials_exception
    return token_data

async def get_current_active_user(token_data: Annotated[TokenData, Depends(get_current_user_token)]):
    """
    Dependency to ensure the user is active (username exists).
    In a real app, this would fetch user from DB and check if active.
    For this example, we just check if username is present.
    """
    if token_data.username is None:
        raise UnauthorizedException(detail="User not found or inactive.")
    return token_data.username

def has_role(required_role: str):
    """
    Dependency factory to check if the current user has a specific role.
    This assumes roles are part of the JWT scopes or can be derived from the user object.
    """
    def role_checker(token_data: Annotated[TokenData, Depends(get_current_user_token)]):
        # In a real application, you'd fetch the user from the DB using token_data.username
        # and check their role. For simplicity, we assume roles are in scopes.
        if required_role not in token_data.scopes:
            logger.warning(f"User {token_data.username} attempted to access resource without required role: {required_role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have the required role: {required_role}"
            )
        return True
    return role_checker