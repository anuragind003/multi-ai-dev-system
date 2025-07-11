from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.crud import CRUDUser, CRUDRole
from app.models import User, Role
from app.schemas import UserCreate, UserLogin, UserSeed, RoleCreate
from app.security import get_password_hash, verify_password, create_access_token
from app.exceptions import (
    UserAlreadyExistsException, InvalidCredentialsException, NotFoundException,
    ForbiddenException, UnauthorizedException
)
from app.config import settings
from app.utils.logger import logger

class UserService:
    """
    Business logic layer for user management.
    Handles user registration, authentication, and initial user seeding.
    """
    def __init__(self, user_crud: CRUDUser, role_crud: CRUDRole):
        self.user_crud = user_crud
        self.role_crud = role_crud

    async def register_user(self, db: Session, user_data: UserCreate) -> User:
        """
        Registers a new user.
        - Checks if the user already exists.
        - Hashes the password.
        - Retrieves or creates the specified role.
        - Creates the user in the database.
        """
        logger.info(f"Attempting to register user: {user_data.email}")
        existing_user = self.user_crud.get_by_email(db, email=user_data.email)
        if existing_user:
            logger.warning(f"Registration failed: User with email {user_data.email} already exists.")
            raise UserAlreadyExistsException(f"User with email '{user_data.email}' already exists.")

        role = self.role_crud.get_by_name(db, name=user_data.role_name)
        if not role:
            logger.info(f"Role '{user_data.role_name}' not found, creating it.")
            try:
                role = self.role_crud.create_role(db, RoleCreate(name=user_data.role_name))
            except IntegrityError:
                # Handle race condition if another process creates the role simultaneously
                role = self.role_crud.get_by_name(db, name=user_data.role_name)
                if not role: # Still not found, something is wrong
                    logger.error(f"Failed to create or retrieve role '{user_data.role_name}' during user registration.")
                    raise HTTPException(status_code=500, detail="Could not assign role to user.")
            except Exception as e:
                logger.error(f"Error creating role '{user_data.role_name}': {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to create role for user.")

        hashed_password = get_password_hash(user_data.password)
        user_data.password = hashed_password # Update Pydantic model with hashed password
        
        try:
            db_user = self.user_crud.create_user(db, user_data, role.id)
            logger.info(f"User {db_user.email} registered successfully with role {role.name}.")
            return db_user
        except IntegrityError:
            logger.error(f"Database integrity error during user creation for {user_data.email}.", exc_info=True)
            raise UserAlreadyExistsException(f"User with email '{user_data.email}' already exists (integrity error).")
        except Exception as e:
            logger.error(f"Unexpected error during user registration for {user_data.email}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An unexpected error occurred during registration.")

    async def authenticate_user(self, db: Session, user_login: UserLogin) -> Optional[User]:
        """
        Authenticates a user by verifying their email and password.
        """
        logger.info(f"Attempting to authenticate user: {user_login.email}")
        user = self.user_crud.get_by_email(db, email=user_login.email)
        if not user:
            logger.warning(f"Authentication failed: User {user_login.email} not found.")
            raise InvalidCredentialsException("Incorrect email or password.")
        if not verify_password(user_login.password, user.hashed_password):
            logger.warning(f"Authentication failed: Incorrect password for user {user_login.email}.")
            raise InvalidCredentialsException("Incorrect email or password.")
        if not user.is_active:
            logger.warning(f"Authentication failed: User {user_login.email} is inactive.")
            raise ForbiddenException("User account is inactive.")
        
        logger.info(f"User {user.email} authenticated successfully.")
        return user

    async def create_access_token_for_user(self, user: User) -> str:
        """
        Creates a JWT access token for a given user.
        """
        # Ensure the role is loaded if not already
        if not user.role:
            # This should ideally be handled by eager loading in CRUD or ensuring session is open
            # For robustness, we can explicitly load it if needed.
            # In a typical FastAPI setup with `get_db` and ORM, `user.role` should be available.
            logger.warning(f"User {user.email} role not eagerly loaded. This might indicate a session issue.")
            # If user.role is None, it means the relationship wasn't loaded.
            # This can happen if the session was closed or the object was detached.
            # For this example, we assume the session is active and relationship is loaded.
            # If not, a simple fix would be to re-query the user with `db.query(User).options(joinedload(User.role)).filter(User.id == user.id).first()`
            pass 
        
        roles = [user.role.name] if user.role else []
        access_token = create_access_token(
            data={"sub": user.email, "roles": roles},
            expires_delta=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        logger.info(f"Access token created for user: {user.email}")
        return access_token

    async def get_user_profile(self, db: Session, email: str) -> User:
        """
        Retrieves a user's profile by email.
        """
        user = self.user_crud.get_by_email(db, email=email)
        if not user:
            raise NotFoundException(f"User with email '{email}' not found.")
        return user

    async def seed_initial_users(self, db: Session):
        """
        Seeds initial roles and users (Admin, Team Lead, Process Manager) if they don't exist.
        This is typically called once on application startup.
        """
        logger.info("Checking for initial roles and users to seed...")
        
        # Define roles and their associated initial users
        initial_roles_and_users = [
            {"name": "Admin", "users": [
                {"email": settings.INITIAL_ADMIN_EMAIL, "password": settings.INITIAL_ADMIN_PASSWORD, "first_name": "Super", "last_name": "Admin"}
            ]},
            {"name": "Team Lead", "users": [
                {"email": settings.INITIAL_TEAM_LEAD_EMAIL, "password": settings.INITIAL_TEAM_LEAD_PASSWORD, "first_name": "VKYC", "last_name": "TeamLead"}
            ]},
            {"name": "Process Manager", "users": [
                {"email": settings.INITIAL_PROCESS_MANAGER_EMAIL, "password": settings.INITIAL_PROCESS_MANAGER_PASSWORD, "first_name": "VKYC", "last_name": "ProcessManager"}
            ]},
        ]

        for role_data in initial_roles_and_users:
            role_name = role_data["name"]
            role = self.role_crud.get_by_name(db, name=role_name)
            if not role:
                try:
                    role = self.role_crud.create_role(db, RoleCreate(name=role_name))
                    logger.info(f"Role '{role_name}' created.")
                except IntegrityError:
                    # Handle race condition if another process creates the role simultaneously
                    db.rollback() # Rollback the failed transaction
                    role = self.role_crud.get_by_name(db, name=role_name)
                    if not role:
                        logger.error(f"Failed to create or retrieve role '{role_name}' due to race condition or other error.")
                        continue # Skip users for this role if role creation failed
                except Exception as e:
                    logger.error(f"Error creating role '{role_name}': {e}", exc_info=True)
                    continue # Skip users for this role if role creation failed
            else:
                logger.debug(f"Role '{role_name}' already exists.")

            if role: # Proceed only if role exists or was created
                for user_seed_data in role_data["users"]:
                    user_email = user_seed_data["email"]
                    existing_user = self.user_crud.get_by_email(db, email=user_email)
                    if not existing_user:
                        try:
                            hashed_password = get_password_hash(user_seed_data["password"])
                            user_create_schema = UserCreate(
                                email=user_email,
                                password=hashed_password, # Already hashed
                                first_name=user_seed_data.get("first_name"),
                                last_name=user_seed_data.get("last_name"),
                                role_name=role_name # This field is not used by create_user directly, but for schema consistency
                            )
                            self.user_crud.create_user(db, user_create_schema, role.id)
                            logger.info(f"Initial user '{user_email}' with role '{role_name}' seeded.")
                        except IntegrityError:
                            db.rollback() # Rollback the failed transaction
                            logger.warning(f"User '{user_email}' already exists (race condition during seeding).")
                        except Exception as e:
                            logger.error(f"Error seeding user '{user_email}' for role '{role_name}': {e}", exc_info=True)
                    else:
                        logger.debug(f"User '{user_email}' already exists, skipping seeding.")
        logger.info("Initial user and role seeding process complete.")