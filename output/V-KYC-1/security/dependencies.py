from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import settings
from schemas import TokenData
from models import User, UserRole
from core.exceptions import CustomHTTPException
from core.logging_config import setup_logging

logger = setup_logging()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises HTTPException for invalid or expired tokens.
    """
    credentials_exception = CustomHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
        code="INVALID_TOKEN"
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            logger.warning("JWT payload missing 'sub' (username).")
            raise credentials_exception
        token_data = TokenData(username=username, roles=[UserRole(r) for r in roles])
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}", exc_info=True)
        raise credentials_exception
    
    # In a real application, you would fetch the user from the database here
    # to ensure they are still active and their roles haven't changed.
    # For simplicity, we'll assume the user exists and is active based on token data.
    # from services.auth_service import AuthService
    # from database import get_db
    # async with get_db() as db:
    #     auth_service = AuthService(db)
    #     user = await auth_service.get_user_by_username(token_data.username)
    #     if user is None or not user.is_active:
    #         logger.warning(f"User {token_data.username} from token not found or inactive.")
    #         raise credentials_exception
    #     return user
    
    # Mock User object for demonstration without DB lookup in this dependency
    # In production, always fetch from DB to ensure user is active and roles are current.
    mock_user_role = UserRole.VIEWER
    if token_data.roles:
        mock_user_role = token_data.roles[0] # Take the first role for simplicity
    
    mock_user = User(
        id=1, # Placeholder ID
        username=token_data.username,
        email=f"{token_data.username}@example.com",
        hashed_password="mock_hashed_password",
        role=mock_user_role,
        is_active=True
    )
    logger.debug(f"User '{mock_user.username}' authenticated with role '{mock_user.role}'.")
    return mock_user

def has_role(required_roles: List[UserRole]):
    """
    Dependency to check if the current user has one of the required roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            logger.warning(f"User '{current_user.username}' with role '{current_user.role}' attempted to access resource requiring roles: {required_roles}")
            raise CustomHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                code="INSUFFICIENT_PERMISSIONS"
            )
        logger.debug(f"User '{current_user.username}' has required role '{current_user.role}'.")
        return current_user
    return role_checker