from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from config import get_settings
from database import get_db
from models import User, UserRole
from schemas import TokenData, UserLogin, UserResponse
from exceptions import UnauthorizedException, ForbiddenException
from logger import logger

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

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

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticates a user by username and password."""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserResponse:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises UnauthorizedException if token is invalid or user not found.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise UnauthorizedException(detail="Could not validate credentials - username missing.")
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except JWTError as e:
        logger.warning(f"JWT Error: {e}")
        raise UnauthorizedException(detail="Could not validate credentials - invalid token.")

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise UnauthorizedException(detail="User not found.")
    if not user.is_active:
        raise UnauthorizedException(detail="User is inactive.")

    logger.debug(f"User '{user.username}' authenticated with roles: {user.role}")
    return UserResponse.model_validate(user)

def require_role(required_role: UserRole):
    """
    Dependency factory to enforce role-based access control.
    Usage: Depends(require_role(UserRole.ADMIN))
    """
    def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role.value != required_role.value:
            logger.warning(f"User '{current_user.username}' (role: {current_user.role}) attempted to access resource requiring role: {required_role}")
            raise ForbiddenException(detail=f"User does not have the required role: {required_role.value}")
        logger.debug(f"User '{current_user.username}' has required role: {required_role}")
        return current_user
    return role_checker

def require_any_role(required_roles: list[UserRole]):
    """
    Dependency factory to enforce access control for any of the given roles.
    Usage: Depends(require_any_role([UserRole.ADMIN, UserRole.AUDITOR]))
    """
    def any_role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in required_roles:
            logger.warning(f"User '{current_user.username}' (role: {current_user.role}) attempted to access resource requiring any of roles: {required_roles}")
            raise ForbiddenException(detail=f"User does not have any of the required roles: {[r.value for r in required_roles]}")
        logger.debug(f"User '{current_user.username}' has one of the required roles: {required_roles}")
        return current_user
    return any_role_checker