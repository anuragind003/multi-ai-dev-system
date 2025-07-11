from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings
from app.logger import logger
import asyncio

# SQLAlchemy engine setup
# `pool_pre_ping=True` ensures connections are alive before use.
# `pool_recycle` recycles connections after a certain time to prevent stale connections.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.ECHO_SQL,
    pool_pre_ping=True,
    pool_recycle=3600, # Recycle connections every hour
    connect_args={"options": "-c timezone=utc"} # Ensure UTC timezone for database
)

# SessionLocal for database interactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

async def init_db():
    """
    Initializes the database by creating all tables defined in models.
    Also ensures default roles and permissions are present.
    """
    from app.models import Role, Permission, RolePermission, User # Import models here to avoid circular dependency

    try:
        # Use asyncio.to_thread for synchronous SQLAlchemy operations in async context
        await asyncio.to_thread(Base.metadata.create_all, bind=engine)
        logger.info("Database tables created/verified.")

        with SessionLocal() as db:
            # Check and create default roles and permissions
            default_roles_data = [
                {"name": "admin", "description": "Full administrative access"},
                {"name": "auditor", "description": "Can view and download recordings"},
                {"name": "uploader", "description": "Can upload and manage their own recordings"},
            ]

            default_permissions_data = [
                {"name": "user:read", "description": "View user details"},
                {"name": "user:write", "description": "Create/update user details"},
                {"name": "user:delete", "description": "Delete users"},
                {"name": "role:read", "description": "View role details"},
                {"name": "role:write", "description": "Create/update role details"},
                {"name": "recording:read", "description": "View recording metadata"},
                {"name": "recording:download", "description": "Download recording files"},
                {"name": "recording:upload", "description": "Upload new recordings"},
                {"name": "recording:delete", "description": "Delete recordings"},
                {"name": "bulk_request:read", "description": "View bulk request details"},
                {"name": "bulk_request:write", "description": "Create/update bulk requests"},
            ]

            # Map roles to permissions
            role_permissions_map = {
                "admin": [
                    "user:read", "user:write", "user:delete",
                    "role:read", "role:write",
                    "recording:read", "recording:download", "recording:upload", "recording:delete",
                    "bulk_request:read", "bulk_request:write"
                ],
                "auditor": [
                    "user:read",
                    "recording:read", "recording:download",
                    "bulk_request:read"
                ],
                "uploader": [
                    "recording:read", "recording:upload",
                    "bulk_request:read", "bulk_request:write"
                ]
            }

            for role_data in default_roles_data:
                role = db.query(Role).filter(Role.name == role_data["name"]).first()
                if not role:
                    role = Role(**role_data)
                    db.add(role)
                    db.commit()
                    db.refresh(role)
                    logger.info(f"Default role '{role.name}' created.")

            for perm_data in default_permissions_data:
                permission = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
                if not permission:
                    permission = Permission(**perm_data)
                    db.add(permission)
                    db.commit()
                    db.refresh(permission)
                    logger.info(f"Default permission '{permission.name}' created.")

            # Assign permissions to roles
            for role_name, perm_names in role_permissions_map.items():
                role = db.query(Role).filter(Role.name == role_name).first()
                if role:
                    for perm_name in perm_names:
                        permission = db.query(Permission).filter(Permission.name == perm_name).first()
                        if permission:
                            role_perm = db.query(RolePermission).filter(
                                RolePermission.role_id == role.id,
                                RolePermission.permission_id == permission.id
                            ).first()
                            if not role_perm:
                                role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                                db.add(role_perm)
                                db.commit()
                                logger.info(f"Assigned permission '{permission.name}' to role '{role.name}'.")
            
            # Create default admin user if not exists
            from app.security import get_password_hash
            admin_user = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
            if not admin_user:
                admin_role = db.query(Role).filter(Role.name == "admin").first()
                if admin_role:
                    admin_user = User(
                        email=settings.ADMIN_EMAIL,
                        hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                        first_name="Super",
                        last_name="Admin",
                        is_active=True,
                        role_id=admin_role.id
                    )
                    db.add(admin_user)
                    db.commit()
                    db.refresh(admin_user)
                    logger.info(f"Default admin user '{settings.ADMIN_EMAIL}' created.")
                else:
                    logger.error("Admin role not found, cannot create default admin user.")

    except SQLAlchemyError as e:
        logger.critical(f"Database initialization failed: {e}")
        raise

def get_db():
    """
    Dependency to get a database session.
    Ensures the session is closed after the request is processed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()