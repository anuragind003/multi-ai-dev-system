from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from config import settings
from core.exceptions import UnauthorizedException
from utils.logger import get_logger

logger = get_logger(__name__)

# OAuth2PasswordBearer for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token") # Endpoint for token generation

class Token(BaseModel):
    """Pydantic model for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Pydantic model for data contained within the JWT token."""
    username: Optional[str] = None
    roles: list[str] = Field(default_factory=list)

class User(BaseModel):
    """Pydantic model for a user (used for authentication)."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    roles: list[str] = Field(default_factory=list)

class UserInDB(User):
    """Pydantic model for a user stored in the database (with hashed password)."""
    hashed_password: str

class JWTHandler:
    """
    Handles JWT token creation and verification.
    """
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """
        Creates a new JWT access token.

        Args:
            data (dict): The payload to encode into the token.
            expires_delta (Optional[timedelta]): The timedelta for token expiration.

        Returns:
            str: The encoded JWT token.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.debug(f"Access token created for user: {data.get('sub')}")
        return encoded_jwt

    def verify_token(self, token: str) -> TokenData:
        """
        Verifies a JWT token and returns its payload.

        Args:
            token (str): The JWT token to verify.

        Returns:
            TokenData: The decoded token data.

        Raises:
            UnauthorizedException: If the token is invalid or expired.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            roles: list[str] = payload.get("roles", [])
            if username is None:
                logger.warning("Token verification failed: Username missing in payload.")
                raise UnauthorizedException(detail="Could not validate credentials")
            token_data = TokenData(username=username, roles=roles)
            logger.debug(f"Token verified for user: {username}")
            return token_data
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}", exc_info=True)
            raise UnauthorizedException(detail="Could not validate credentials")
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}", exc_info=True)
            raise UnauthorizedException(detail="Internal server error during authentication")

jwt_handler = JWTHandler()

# --- Dummy User Database (for demonstration) ---
# In a real application, this would interact with a proper user management system (DB, LDAP, SSO)
fake_users_db = {
    "adminuser": {
        "username": "adminuser",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": "fakehashedpassword_admin", # In production, use proper hashing (e.g., bcrypt)
        "disabled": False,
        "roles": ["admin", "process_manager", "team_lead"],
    },
    "pmuser": {
        "username": "pmuser",
        "full_name": "Process Manager",
        "email": "pm@example.com",
        "hashed_password": "fakehashedpassword_pm",
        "disabled": False,
        "roles": ["process_manager", "team_lead"],
    },
    "tluser": {
        "username": "tluser",
        "full_name": "Team Lead",
        "email": "tl@example.com",
        "hashed_password": "fakehashedpassword_tl",
        "disabled": False,
        "roles": ["team_lead"],
    },
    "disableduser": {
        "username": "disableduser",
        "full_name": "Disabled User",
        "email": "disabled@example.com",
        "hashed_password": "fakehashedpassword_disabled",
        "disabled": True,
        "roles": ["team_lead"],
    },
}

def get_user(username: str) -> Optional[UserInDB]:
    """
    Retrieves a user from the dummy database.
    In a real app, this would query your user database.
    """
    if username in fake_users_db:
        user_data = fake_users_db[username]
        return UserInDB(**user_data)
    return None

# --- Authentication Dependencies ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency to get the current authenticated user from the JWT token.

    Args:
        token (str): The JWT token from the Authorization header.

    Returns:
        dict: A dictionary containing the user's username and roles.

    Raises:
        UnauthorizedException: If the token is invalid, expired, or user is not found/disabled.
    """
    token_data = jwt_handler.verify_token(token)
    
    user = get_user(token_data.username)
    if user is None:
        logger.warning(f"Authentication failed: User '{token_data.username}' not found.")
        raise UnauthorizedException(detail="User not found")
    if user.disabled:
        logger.warning(f"Authentication failed: User '{user.username}' is disabled.")
        raise UnauthorizedException(detail="User is disabled")
    
    logger.debug(f"User '{user.username}' authenticated successfully.")
    return {"username": user.username, "roles": user.roles}

# --- Token Endpoint (for demonstration/testing) ---
# In a real app, this would involve password verification
# @router.post("/token", response_model=Token)
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = get_user(form_data.username)
#     if not user or user.hashed_password != f"fakehashedpassword_{form_data.username}": # Dummy password check
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = jwt_handler.create_access_token(
#         data={"sub": user.username, "roles": user.roles}, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token, "token_type": "bearer"}