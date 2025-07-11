from sqlalchemy.orm import Session
from app.models import User
from app.schemas import UserCreate
from app.security import get_password_hash, verify_password
from app.error_handling import CustomHTTPException
from app.utils.logger import get_logger
from fastapi import status

logger = get_logger(__name__)

class UserService:
    """
    Service layer for user-related business logic.
    Handles interactions with the database for user management.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> User | None:
        """
        Retrieves a user by their username.
        """
        logger.debug(f"Attempting to retrieve user: {username}")
        user = self.db.query(User).filter(User.username == username).first()
        if user:
            logger.debug(f"User '{username}' found.")
        else:
            logger.debug(f"User '{username}' not found.")
        return user

    def create_user(self, user_data: UserCreate) -> User:
        """
        Creates a new user in the database.
        Hashes the password before storing.
        Raises CustomHTTPException if username or email already exists.
        """
        logger.info(f"Attempting to create new user: {user_data.username}")

        # Check if username already exists
        if self.get_user_by_username(user_data.username):
            logger.warning(f"User creation failed: Username '{user_data.username}' already registered.")
            raise CustomHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )
        
        # Check if email already exists (if provided)
        if user_data.email:
            existing_email_user = self.db.query(User).filter(User.email == user_data.email).first()
            if existing_email_user:
                logger.warning(f"User creation failed: Email '{user_data.email}' already registered.")
                raise CustomHTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )

        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            hashed_password=hashed_password,
            email=user_data.email
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        logger.info(f"User '{user_data.username}' created successfully.")
        return db_user

    def authenticate_user(self, username: str, password: str) -> User | None:
        """
        Authenticates a user by checking username and password.
        Returns the user object if credentials are valid, otherwise None.
        """
        logger.info(f"Attempting to authenticate user: {username}")
        user = self.get_user_by_username(username)
        if not user:
            logger.warning(f"Authentication failed for '{username}': User not found.")
            return None
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed for '{username}': Invalid password.")
            return None
        
        logger.info(f"User '{username}' authenticated successfully.")
        return user