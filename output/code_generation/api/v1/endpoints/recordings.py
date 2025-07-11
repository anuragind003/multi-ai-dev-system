### FILE: main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from config import get_settings
from database import init_db, async_engine
from utils.logger import logger
from utils.exceptions import APIException
from middleware.error_handler import ExceptionHandlingMiddleware
from middleware.security import rate_limit_middleware, get_password_hash, MOCK_USERS_DB
from schemas import HealthCheckResponse, Token, UserLogin
from jose import jwt
from passlib.context import CryptContext
from services.audit_log_service import AuditLogService # For dependency injection example
from database import get_db_session # For dependency injection example
from sqlalchemy.ext.asyncio import AsyncSession

# Import API routers
from api.v1.endpoints import audit_logs, recordings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Initializes the database and performs cleanup.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    # Database initialization
    await init_db()
    logger.info("Database initialized.")

    # Add a mock recording metadata for testing
    from models import RecordingMetadata
    from sqlalchemy.future import select
    async with get_db_session() as db:
        existing_meta = await db.execute(select(RecordingMetadata).where(RecordingMetadata.lan_id == "LAN12345"))
        if not existing_meta.scalars().first():
            mock_recording = RecordingMetadata(
                lan_id="LAN12345",
                file_path="path/to/recording_LAN12345.mp4",
                file_size_bytes=1024 * 1024 * 50 # 50 MB
            )
            db.add(mock_recording)
            await db.commit()
            logger.info("Added mock recording metadata for LAN12345.")
        
        existing_meta_2 = await db.execute(select(RecordingMetadata).where(RecordingMetadata.lan_id == "LAN67890"))
        if not existing_meta_2.scalars().first():
            mock_recording_2 = RecordingMetadata(
                lan_id="LAN67890",
                file_path="path/to/recording_LAN67890.mp4",
                file_size_bytes=1024 * 1024 * 75 # 75 MB
            )
            db.add(mock_recording_2)
            await db.commit()
            logger.info("Added mock recording metadata for LAN67890.")

    # Create a dummy file for testing file access
    dummy_file_path = os.path.join(settings.NFS_MOUNT_POINT, "path/to/recording_LAN12345.mp4")
    os.makedirs(os.path.dirname(dummy_file_path), exist_ok=True)
    if not os.path.exists(dummy_file_path):
        with open(dummy_file_path, "wb") as f:
            f.write(b"This is a dummy video recording content." * 1000) # Create a small dummy file
        logger.info(f"Created dummy file at {dummy_file_path}")

    dummy_file_path_2 = os.path.join(settings.NFS_MOUNT_POINT, "path/to/recording_LAN67890.mp4")
    os.makedirs(os.path.dirname(dummy_file_path_2), exist_ok=True)
    if not os.path.exists(dummy_file_path_2):
        with open(dummy_file_path_2, "wb") as f:
            f.write(b"This is another dummy video recording content." * 1500)
        logger.info(f"Created dummy file at {dummy_file_path_2}")

    yield # Application runs

    # Cleanup on shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    # Close database connections (handled by async_engine context manager implicitly)
    # Clean up dummy files
    if os.path.exists(dummy_file_path):
        os.remove(dummy_file_path)
        logger.info(f"Cleaned up dummy file: {dummy_file_path}")
    if os.path.exists(dummy_file_path_2):
        os.remove(dummy_file_path_2)
        logger.info(f"Cleaned up dummy file: {dummy_file_path_2}")
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# --- Middleware ---
app.add_middleware(ExceptionHandlingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
app.middleware("http")(rate_limit_middleware) # Apply rate limiting

# --- API Routers ---
app.include_router(audit_logs.router, prefix="/api/v1", tags=["Audit Logs"])
app.include_router(recordings.router, prefix="/api/v1", tags=["Recordings"])

# --- Authentication Endpoint ---
@app.post(
    "/token",
    response_model=Token,
    summary="Obtain JWT access token",
    description="Authenticates a user and returns a JWT access token for subsequent API calls.",
    tags=["Authentication"]
)
async def login_for_access_token(form_data: UserLogin):
    """
    Authenticates a user and returns a JWT access token.
    """
    user_in_db = MOCK_USERS_DB.get(form_data.username) # In real app, fetch from DB
    if not user_in_db or not pwd_context.verify(form_data.password, user_in_db["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user_in_db["username"], "scopes": [user_in_db["role"]]},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    logger.info(f"User '{form_data.username}' successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

# --- Health Check Endpoint ---
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Provides the current status of the API and its dependencies (database, NFS).",
    tags=["Monitoring"]
)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """
    Performs a health check on the application and its dependencies.
    """
    db_status = "unhealthy"
    nfs_status = "unhealthy"

    try:
        # Check database connection
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"unhealthy: {e}"

    try:
        # Check NFS mount point accessibility
        # This is a basic check; a more robust check might involve writing/reading a small test file
        if os.path.exists(settings.NFS_MOUNT_POINT) and os.access(settings.NFS_MOUNT_POINT, os.R_OK):
            nfs_status = "healthy"
        else:
            nfs_status = "unhealthy: mount point not accessible or does not exist"
    except Exception as e:
        logger.error(f"NFS health check failed: {e}")
        nfs_status = f"unhealthy: {e}"

    logger.debug(f"Health check performed: DB={db_status}, NFS={nfs_status}")
    return HealthCheckResponse(
        status="healthy" if db_status == "healthy" and nfs_status == "healthy" else "degraded",
        timestamp=datetime.now(timezone.utc),
        version=settings.APP_VERSION,
        database_status=db_status,
        nfs_status=nfs_status
    )

# --- Dependency Injection Example (not directly used in endpoints, but shows pattern) ---
def get_audit_log_service(db: AsyncSession = Depends(get_db_session)) -> AuditLogService:
    """
    Dependency that provides an AuditLogService instance.
    """
    return AuditLogService(db)

# Example of how to use it (not a real endpoint, just for illustration)
@app.get("/example-di", include_in_schema=False)
async def example_dependency_injection(
    audit_service: AuditLogService = Depends(get_audit_log_service)
):
    # You can now use audit_service methods directly
    # e.g., logs = await audit_service.get_audit_logs()
    return {"message": "AuditLogService injected successfully"}