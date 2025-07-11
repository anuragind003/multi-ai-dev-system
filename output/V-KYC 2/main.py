from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from config import settings
from database import init_db, get_db
from utils.logger import logger, setup_logging
from utils.error_handlers import register_error_handlers
from api.v1.endpoints import user_routes, rbac_protected_routes
from schemas import HealthCheckResponse
from models import UserRole, Role # Import Role and UserRole for initial data seeding

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Initializes database and sets up logging.
    """
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} environment...")
    
    # Database initialization
    try:
        init_db()
        # Seed roles if they don't exist
        with next(get_db()) as db:
            for role_name in UserRole:
                if not db.query(Role).filter(Role.name == role_name).first():
                    db.add(Role(name=role_name))
                    db.commit()
                    logger.info(f"Seeded role: {role_name.value}")
        logger.info("Database and roles initialized successfully.")
    except OperationalError as e:
        logger.critical(f"Database connection failed on startup: {e}")
        # Depending on the deployment strategy, you might want to exit or retry
        # For now, we'll let the app start but health check will fail.
    except Exception as e:
        logger.critical(f"Error during database initialization: {e}")

    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")

app = FastAPI(
    title=settings.APP_NAME,
    description="A FastAPI backend for VKYC Portal with Role-Based Access Control.",
    version=settings.VERSION if hasattr(settings, 'VERSION') else "1.0.0", # Assuming VERSION might be in settings
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Register global exception handlers
register_error_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = settings.X_FRAME_OPTIONS
    response.headers["X-Content-Type-Options"] = settings.X_CONTENT_TYPE_OPTIONS
    response.headers["X-XSS-Protection"] = settings.X_XSS_PROTECTION
    response.headers["Strict-Transport-Security"] = settings.STRICT_TRANSPORT_SECURITY
    response.headers["Referrer-Policy"] = settings.REFERRER_POLICY
    return response

# Include API routers
app.include_router(user_routes.router, prefix="/api/v1")
app.include_router(rbac_protected_routes.router, prefix="/api/v1")

@app.get("/health", response_model=HealthCheckResponse, summary="Health Check Endpoint")
async def health_check(db: Session = Depends(get_db)):
    """
    Provides a health check endpoint for monitoring.
    Checks database connectivity.
    """
    db_status = "ok"
    try:
        # Perform a simple query to check database connectivity
        db.execute(db.text("SELECT 1"))
    except OperationalError as e:
        db_status = f"error: {e}"
        logger.error(f"Database health check failed: {e}")
    except Exception as e:
        db_status = f"error: {e}"
        logger.error(f"Unexpected error during database health check: {e}")

    if "error" in db_status:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheckResponse(
                status="unhealthy",
                message="Service is unhealthy",
                database_status=db_status
            ).model_dump()
        )
    
    logger.info("Health check successful.")
    return HealthCheckResponse(database_status=db_status)

if __name__ == "__main__":
    import uvicorn
    # To run: uvicorn main:app --reload --port 8000
    # For production: uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG_MODE)