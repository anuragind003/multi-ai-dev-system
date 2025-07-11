import datetime
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.config import settings
from core.exceptions import UnauthorizedException, ForbiddenException
from database import get_db
from models.models import User, UserRole
from schemas.schemas import TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    scopes={
        "me": "Read current user info",
        "users:read": "Read all users",
        "users:write": "Create/Update/Delete users",
        "test_cases:read": "Read test cases",
        "test_cases:write": "Create/Update/Delete test cases",
        "test_runs:read": "Read test runs",
        "test_runs:write": "Create/Update/Delete test runs",
        "test_runs:execute": "Execute test runs"
    }
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises UnauthorizedException if token is invalid or user not found.
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    credentials_exception = UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).filter(User.username == token_data.username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    
    # Check if user has required scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise ForbiddenException(detail=f"Not enough permissions: Missing scope '{scope}'")
            
    if not user.is_active:
        raise ForbiddenException(detail="Inactive user")
        
    return user

def has_permission(required_roles: list[UserRole]):
    """
    Dependency factory to check if the current user has one of the required roles.
    """
    async def _has_permission(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise ForbiddenException(detail=f"User does not have required role. Required: {', '.join(r.value for r in required_roles)}")
        return current_user
    return _has_permission