from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
import logging

from config import settings
from core.error_handling import UnauthorizedException, ForbiddenException

logger = logging.getLogger(__name__)

# --- User Model (for internal representation) ---
class User(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    is_active: bool = True

# --- Token Data Model ---
class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = Field(default_factory=list)

# --- OAuth2 Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # "token" is the endpoint where clients can get a token

# --- JWT Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception: HTTPException):
    """
    Verifies a JWT token and returns the decoded payload.
    Raises HTTPException if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=roles)
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise credentials_exception
    return token_data

# --- Authentication Dependencies ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the current authenticated user.
    Raises UnauthorizedException if authentication fails.
    """
    credentials_exception = UnauthorizedException(detail="Could not validate credentials")
    token_data = verify_token(token, credentials_exception)
    
    # In a real application, you would fetch the user from a database
    # For this example, we'll mock a user based on the token data
    # This mock user should ideally come from a user service/DB
    mock_users_db = {
        "admin_user": {"id": 1, "username": "admin_user", "email": "admin@example.com", "roles": [settings.ADMIN_ROLE, settings.PROCESS_MANAGER_ROLE]},
        "tl_user": {"id": 2, "username": "tl_user", "email": "tl@example.com", "roles": [settings.TL_ROLE]},
        "basic_user": {"id": 3, "username": "basic_user", "email": "user@example.com", "roles": [settings.USER_ROLE]},
    }
    
    user_data = mock_users_db.get(token_data.username)
    if user_data is None:
        raise credentials_exception
    
    user = User(**user_data)
    if not user.is_active:
        raise UnauthorizedException(detail="Inactive user")
    
    return user

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """
    Dependency to get the current authenticated user, or None if no token is provided or invalid.
    Useful for logging or endpoints that don't strictly require authentication.
    """
    if token is None:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None # Silently fail if token is invalid for optional auth

# --- Authorization Dependencies ---
def has_role(required_roles: List[str]):
    """
    Dependency factory to check if the current user has any of the required roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if not any(role in current_user.roles for role in required_roles):
            logger.warning(f"User '{current_user.username}' attempted to access forbidden resource. Roles: {current_user.roles}, Required: {required_roles}")
            raise ForbiddenException(detail=f"User does not have required roles: {', '.join(required_roles)}")
        return current_user
    return role_checker

# Example usage for generating a token (for testing/development)
if __name__ == "__main__":
    # Example: Generate a token for an admin user
    admin_token_data = {"sub": "admin_user", "roles": [settings.ADMIN_ROLE, settings.PROCESS_MANAGER_ROLE]}
    admin_token = create_access_token(admin_token_data)
    print(f"Admin User Token: {admin_token}")

    # Example: Generate a token for a team lead user
    tl_token_data = {"sub": "tl_user", "roles": [settings.TL_ROLE]}
    tl_token = create_access_token(tl_token_data)
    print(f"Team Lead User Token: {tl_token}")

    # Example: Generate a token for a basic user
    basic_token_data = {"sub": "basic_user", "roles": [settings.USER_ROLE]}
    basic_token = create_access_token(basic_token_data)
    print(f"Basic User Token: {basic_token}")

    # Example: Verify a token
    try:
        verified_data = verify_token(admin_token, HTTPException(status_code=401, detail="Invalid token"))
        print(f"Verified Admin Token Data: {verified_data.model_dump()}")
    except HTTPException as e:
        print(f"Token verification failed: {e.detail}")

    # Example: Test role checking (requires running FastAPI app to test with Depends)
    # This part is conceptual for how it would be used in an endpoint.