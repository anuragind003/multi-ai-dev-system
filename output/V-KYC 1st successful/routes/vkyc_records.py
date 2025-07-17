### FILE: main.py
from fastapi import FastAPI, status, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from config import get_settings
from database import init_db, get_db
from models import Base, Role, User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from utils.logger import logger
from middleware import setup_global_middleware
from handlers import (
    credential_exception_handler,
    permission_denied_exception_handler,
    not_found_exception_handler,
    duplicate_entry_exception_handler,
    bad_request_exception_handler,
    generic_exception_handler
)
from exceptions import (
    CredentialException,
    PermissionDeniedException,
    NotFoundException,
    DuplicateEntryException,
    BadRequestException
)

# Import routers
from routes import auth as auth_routes
from routes import users as users_routes
from routes import vkyc_records as vkyc_records_routes
from schemas import HealthCheckResponse

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Initializes the database and creates default roles/admin user.
    """
    logger.info(f"Starting up {settings.APP_NAME} v{settings.APP_VERSION}...")
    await init_db()
    
    # Create default roles if they don't exist
    async with get_db() as db:
        for role_name in ["admin", "process_manager", "team_lead"]:
            existing_role = await db.execute(select(Role).where(Role.name == role_name))
            if not existing_role.scalar_one_or_none():
                db.add(Role(name=role_name))
                logger.info(f"Created default role: {role_name}")
        await db.commit()

        # Create a default admin user if not exists (for initial setup)
        from auth import get_password_hash # Import here to avoid circular dependency
        existing_admin = await db.execute(select(User).where(User.username == "admin"))
        if not existing_admin.scalar_one_or_none():
            admin_role = await db.execute(select(Role).where(Role.name == "admin"))
            admin_role = admin_role.scalar_one_or_none()
            if admin_role:
                db.add(User(
                    username="admin",
                    email="admin@example.com",
                    hashed_password=get_password_hash("adminpassword"), # CHANGE THIS IN PRODUCTION!
                    is_active=True,
                    role_id=admin_role.id
                ))
                await db.commit()
                logger.info("Created default admin user: admin/adminpassword")
            else:
                logger.error("Admin role not found, cannot create default admin user.")

    logger.info("Application startup complete.")
    yield
    logger.info("Shutting down application...")
    # Perform cleanup here if necessary

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Register global exception handlers
app.add_exception_handler(CredentialException, credential_exception_handler)
app.add_exception_handler(PermissionDeniedException, permission_denied_exception_handler)
app.add_exception_handler(NotFoundException, not_found_exception_handler)
app.add_exception_handler(DuplicateEntryException, duplicate_entry_exception_handler)
app.add_exception_handler(BadRequestException, bad_request_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler) # Catch-all for unhandled exceptions

# Setup global middleware
setup_global_middleware(app)

# Include API routers
app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(vkyc_records_routes.router)

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    status_code=status.HTTP_200_OK
)
async def health_check():
    """
    Returns the health status of the API.
    """
    logger.debug("Health check requested.")
    return HealthCheckResponse(
        status="ok",
        version=settings.APP_VERSION,
        service=settings.APP_NAME
    )