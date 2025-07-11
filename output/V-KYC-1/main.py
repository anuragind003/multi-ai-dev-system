import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from database import init_db, close_db_connection, get_db
from routers import users
from middleware.cors_headers import add_cors_and_security_headers
from utils.exceptions import NotFoundException, ConflictException, UnauthorizedException, ForbiddenException, ValidationException
from utils.error_handlers import (
    not_found_exception_handler,
    conflict_exception_handler,
    unauthorized_exception_handler,
    forbidden_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from utils.logger import get_logger
from schemas import HealthCheckResponse

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Initializes the database connection pool on startup and closes it on shutdown.
    """
    logger.info("Application startup: Initializing database...")
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Application shutdown: Closing database connection...")
    await close_db_connection()
    logger.info("Database connection closed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="A robust FastAPI backend for V-KYC Portal, managing user authentication and recording metadata.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Register global exception handlers
app.add_exception_handler(NotFoundException, not_found_exception_handler)
app.add_exception_handler(ConflictException, conflict_exception_handler)
app.add_exception_handler(UnauthorizedException, unauthorized_exception_handler)
app.add_exception_handler(ForbiddenException, forbidden_exception_handler)
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Add CORS and security headers middleware
add_cors_and_security_headers(app)

# Include API routers
app.include_router(users.router, prefix="/api/v1", tags=["Users", "Authentication"])

@app.get("/health", response_model=HealthCheckResponse, summary="Health Check", tags=["Monitoring"])
async def health_check():
    """
    Provides a simple health check endpoint to verify application status.
    """
    try:
        # Attempt to get a database session to verify DB connectivity
        async with get_db() as db:
            # Execute a simple query to check DB connection
            await db.execute("SELECT 1")
        logger.info("Health check successful: Database connection OK.")
        return HealthCheckResponse(status="healthy", message="Service is up and running. Database connection OK.")
    except Exception as e:
        logger.error(f"Health check failed: Database connection error - {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service is unhealthy: Database connection failed. Error: {e}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        log_level="info" if not settings.DEBUG_MODE else "debug"
    )