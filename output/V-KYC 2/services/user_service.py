from sqlalchemy.orm import Session
from models import User, Role, UserRole
from schemas import UserCreate, LoginRequest
from security import get_password_hash, verify_password
from utils.exceptions import HTTPConflict, HTTPNotFound, HTTPUnauthorized
from utils.logger import logger

class UserService:
    """
    Service layer for user-related business logic.
    Handles user creation, authentication, and retrieval.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> User | None:
        """Retrieves a user by their username."""
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, user_data: UserCreate) -> User:
        """
        Creates a new user in the database.
        Raises HTTPConflict if username already exists.
        """
        if self.get_user_by_username(user_data.username):
            logger.warning(f"Attempted to create user with existing username: {user_data.username}")
            raise HTTPConflict(detail="Username already registered")

        hashed_password = get_password_hash(user_data.password)
        
        # Ensure role exists or create it
        role = self.db.query(Role).filter(Role.name == user_data.role).first()
        if not role:
            logger.info(f"Role '{user_data.role.value}' not found, creating it.")
            role = Role(name=user_data.role)
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)

        db_user = User(
            username=user_data.username,
            hashed_password=hashed_password,
            role_id=role.id
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        logger.info(f"User '{db_user.username}' created with role '{user_data.role.value}'.")
        return db_user

    def authenticate_user(self, login_data: LoginRequest) -> User:
        """
        Authenticates a user based on username and password.
        Raises HTTPUnauthorized if authentication fails.
        """
        user = self.get_user_by_username(login_data.username)
        if not user or not verify_password(login_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {login_data.username}")
            raise HTTPUnauthorized(detail="Incorrect username or password")
        logger.info(f"User '{user.username}' authenticated successfully.")
        return user