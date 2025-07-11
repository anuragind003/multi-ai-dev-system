from fastapi import FastAPI, Depends, HTTPException, status
from contextlib import asynccontextmanager
from database import init_db, get_db
from logger import logger
from config import get_settings
from middleware import setup_middleware, limiter
from error_handlers import register_error_handlers
from api.v1 import endpoints as v1_endpoints
from monitoring import router as monitoring_router
from repositories import UserRepository
from schemas import UserCreate
from models import UserRole

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Initializes database and creates a default admin user if not exists.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    init_db() # Initialize database tables

    # Create a default admin user if not exists
    db = next(get_db()) # Get a session for startup
    user_repo = UserRepository(db)
    try:
        if not user_repo.get_user_by_username("admin"):
            logger.info("Creating default admin user...")
            admin_user_data = UserCreate(
                username="admin",
                email="admin@example.com",
                password="adminpassword", # IMPORTANT: Change this in production!
                full_name="System Administrator",
                role=UserRole.ADMIN
            )
            user_repo.create_user(admin_user_data)
            logger.info("Default admin user 'admin' created. Please change default password immediately!")
        else:
            logger.info("Default admin user 'admin' already exists.")
    except Exception as e:
        logger.error(f"Failed to create default admin user: {e}", exc_info=True)
    finally:
        db.close()

    yield # Application runs

    logger.info(f"Shutting down {settings.APP_NAME}...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for managing VKYC Recording metadata and access.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan # Register the lifespan context manager
)

# Register global exception handlers
register_error_handlers(app)

# Setup middleware (CORS, Security Headers, Rate Limiting)
setup_middleware(app)

# Include API routers
app.include_router(v1_endpoints.router)
app.include_router(monitoring_router) # Health check endpoint

# Add rate limiter to all routes by default
# This is handled by `setup_middleware` and `slowapi.ext.fastapi_limiter.decorators.rate_limit`
# on individual endpoints. No need for a global dependency here if using decorators.

@app.get("/", include_in_schema=False)
async def root():
    """Redirects to API documentation."""
    return {"message": f"Welcome to {settings.APP_NAME}! Visit /docs for API documentation."}

if __name__ == "__main__":
    import uvicorn
    # To run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    # Ensure .env file is present or environment variables are set.
    logger.info(f"Running Uvicorn server on http://0.0.0.0:8000 (Debug: {settings.DEBUG})")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG, # Reloads on code changes if DEBUG is True
        log_level=settings.LOG_LEVEL.lower()
    )