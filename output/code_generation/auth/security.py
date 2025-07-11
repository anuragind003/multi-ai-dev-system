import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from db.models import User
from db.database import SessionLocal # Direct import for initial user creation

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_user_by_username(db: SessionLocal, username: str) -> Optional[User]:
    """Retrieves a user by username from the database."""
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: SessionLocal, username: str, password: str) -> Optional[User]:
    """Authenticates a user by username and password."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_initial_admin_user():
    """
    Creates an initial admin user if one does not exist.
    This function is for development/initial setup purposes.
    In production, manage initial users securely (e.g., through migrations or dedicated scripts).
    """
    db = SessionLocal()
    try:
        admin_user = get_user_by_username(db, settings.ADMIN_USERNAME)
        if not admin_user:
            hashed_password = get_password_hash(settings.ADMIN_PASSWORD.get_secret_value())
            new_admin = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=hashed_password,
                email=f"{settings.ADMIN_USERNAME}@example.com",
                full_name="System Admin",
                is_active=True,
                is_admin=True,
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            logger.info(f"Initial admin user '{settings.ADMIN_USERNAME}' created successfully.")
        else:
            logger.info(f"Admin user '{settings.ADMIN_USERNAME}' already exists.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating initial admin user: {e}", exc_info=True)
    finally:
        db.close()

# Call this function on application startup (e.g., in main.py's lifespan)
# For this example, we'll call it directly here for simplicity, but a better place
# would be in the `lifespan` function of `main.py` after `Base.metadata.create_all`.
# create_initial_admin_user() # Commented out to avoid direct execution on import.
                               # Should be called explicitly from main.py's lifespan.