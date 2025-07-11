from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import DuplicateUserException, UserNotFoundException, InvalidCredentialsException
import logging

logger = logging.getLogger(__name__)

class UserService:
    """
    Service layer for user-related business logic.
    Handles interactions with the database and applies business rules.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_username_or_email(self, identifier: str) -> User | None:
        """
        Retrieves a user by their username or email address.
        """
        stmt = select(User).where((User.username == identifier) | (User.email == identifier))
        result = await self.db.execute(stmt)
        user = result.scalars().first()
        logger.debug(f"Attempted to retrieve user by identifier '{identifier}'. Found: {user is not None}")
        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Creates a new user in the database.
        Hashes the password before saving.
        Raises DuplicateUserException if username or email already exists.
        """
        # Check for existing user by username or email
        existing_user = await self.get_user_by_username_or_email(user_data.username)
        if existing_user:
            raise DuplicateUserException(detail="Username already registered")
        
        existing_user = await self.get_user_by_username_or_email(user_data.email)
        if existing_user:
            raise DuplicateUserException(detail="Email already registered")

        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            is_admin=False # Default to non-admin
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        logger.info(f"User '{db_user.username}' created successfully.")
        return db_user

    async def authenticate_user(self, user_login: UserLogin) -> User:
        """
        Authenticates a user by verifying their username/email and password.
        Raises InvalidCredentialsException if authentication fails.
        """
        user = await self.get_user_by_username_or_email(user_login.username_or_email)
        if not user:
            logger.warning(f"Authentication failed: User '{user_login.username_or_email}' not found.")
            raise InvalidCredentialsException()
        
        if not verify_password(user_login.password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for user '{user.username}'.")
            raise InvalidCredentialsException()
        
        if not user.is_active:
            logger.warning(f"Authentication failed: User '{user.username}' is inactive.")
            raise InvalidCredentialsException(detail="Inactive user")
        
        logger.info(f"User '{user.username}' authenticated successfully.")
        return user