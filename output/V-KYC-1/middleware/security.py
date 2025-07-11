from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database import get_db
from models import User, UserRole
from schemas import TokenData
from utils.exceptions import UnauthorizedException, ForbiddenException
from utils.logger import get_logger
from services import UserService # Import UserService to fetch user from DB

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    Args:
        data (dict): Payload to encode in the token.
        expires_delta (Optional[timedelta]): Optional timedelta for token expiration.
    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises UnauthorizedException if token is invalid or user not found/inactive.
    """
    credentials_exception = UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", []) # Get roles from token payload
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=[UserRole(role) for role in roles])
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}", exc_info=True)
        raise credentials_exception

    user_service = UserService(db)
    user = await user_service.user_repo.get_by_username(token_data.username) # Directly use repo for simplicity here
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise UnauthorizedException(detail="Inactive user", headers={"WWW-Authenticate": "Bearer"})
    
    logger.debug(f"Current user: {user.username} with roles: {user.role.value}")
    return user

def require_role(required_roles: List[UserRole]):
    """
    Dependency factory to enforce role-based access control.
    Args:
        required_roles (List[UserRole]): A list of roles that are allowed to access the endpoint.
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            logger.warning(f"User {current_user.username} (role: {current_user.role.value}) attempted to access restricted resource requiring roles: {[r.value for r in required_roles]}")
            raise ForbiddenException(detail="Not enough permissions to perform this action.")
        logger.debug(f"User {current_user.username} has required role: {current_user.role.value}")
        return current_user
    return role_checker