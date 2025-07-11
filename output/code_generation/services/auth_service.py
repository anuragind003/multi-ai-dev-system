from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
import logging

from crud.user_crud import UserCRUD
from schemas import UserCreate, UserResponse, Token, LoginRequest, TokenData
from core.security import verify_password, get_password_hash, create_access_token, verify_token
from core.exceptions import UnauthorizedException, NotFoundException, ConflictException

logger = logging.getLogger(__name__)

class AuthService:
    """
    Service layer for user authentication and authorization.
    Handles user registration, login, token generation, and current user retrieval.
    """
    def __init__(self, user_crud: UserCRUD):
        self.user_crud = user_crud

    async def register_user(self, user_in: UserCreate) -> UserResponse:
        """
        Registers a new user.
        Hashes the password and stores the user in the database.
        Raises ConflictException if username or email already exists.
        """
        existing_user = await self.user_crud.get_user_by_username(user_in.username)
        if existing_user:
            raise ConflictException(f"Username '{user_in.username}' already registered.")
        
        existing_email = await self.user_crud.get_user_by_email(user_in.email)
        if existing_email:
            raise ConflictException(f"Email '{user_in.email}' already registered.")

        hashed_password = get_password_hash(user_in.password)
        user = await self.user_crud.create_user(user_in, hashed_password)
        logger.info(f"User '{user.username}' successfully registered.")
        return UserResponse.model_validate(user)

    async def authenticate_user(self, login_data: LoginRequest) -> Token:
        """
        Authenticates a user by username and password.
        Generates an access token upon successful authentication.
        Raises UnauthorizedException for invalid credentials.
        """
        user = await self.user_crud.get_user_by_username(login_data.username)
        if not user or not verify_password(login_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {login_data.username}")
            raise UnauthorizedException("Incorrect username or password.")
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {login_data.username}")
            raise UnauthorizedException("User account is inactive.")

        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id, "roles": [user.role]}
        )
        logger.info(f"User '{user.username}' successfully authenticated.")
        return Token(access_token=access_token)

    async def get_current_user(self, token: str) -> UserResponse:
        """
        Retrieves the current authenticated user from a JWT token.
        Raises UnauthorizedException if the token is invalid or user is not found/inactive.
        """
        token_data: TokenData = verify_token(token)
        if token_data.username is None:
            raise UnauthorizedException("Could not validate credentials: Token missing username.")
        
        user = await self.user_crud.get_user_by_username(token_data.username)
        if user is None or not user.is_active:
            logger.warning(f"Attempted access with invalid/inactive token for user: {token_data.username}")
            raise UnauthorizedException("Could not validate credentials: User not found or inactive.")
        
        return UserResponse.model_validate(user)