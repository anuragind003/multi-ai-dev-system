import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from fastapi_secure_headers import SecureHeadersMiddleware

from config import settings
from database import init_db, close_db, get_db
from app.api.v1.api import api_router
from app.core.exceptions import (
    NotFoundException, UnauthorizedException, ForbiddenException, ConflictException,
    http_exception_handler, validation_exception_handler, custom_exception_handler
)
from app.core.middlewares import setup_rate_limiting, setup_secure_headers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Initializes database connection and rate limiter on startup,
    and closes them on shutdown.
    """
    logger.info("Application startup: Initializing database and rate limiter...")
    await init_db()
    await setup_rate_limiting(app)
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown: Closing database and rate limiter...")
    await close_db()
    if FastAPILimiter.redis:
        await FastAPILimiter.redis.close()
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="API for Security Testing Management (Penetration Testing, Vulnerability Scanning)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# --- Global Exception Handlers ---
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(NotFoundException, custom_exception_handler)
app.add_exception_handler(UnauthorizedException, custom_exception_handler)
app.add_exception_handler(ForbiddenException, custom_exception_handler)
app.add_exception_handler(ConflictException, custom_exception_handler)

# --- Middleware Configuration ---
# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
app.add_middleware(SecureHeadersMiddleware)

# Rate Limiting is set up in lifespan context manager

# --- API Routers ---
app.include_router(api_router, prefix=settings.API_V1_STR)

# --- Health Check and Monitoring Endpoints ---
@app.get("/health", summary="Health Check", tags=["Monitoring"])
async def health_check():
    """
    Checks the health of the application.
    Returns 200 OK if the application is running.
    """
    return {"status": "ok", "message": "Application is healthy"}

@app.get("/status", summary="Application Status", tags=["Monitoring"])
async def application_status(db_session=Depends(get_db)):
    """
    Provides detailed application status, including database connectivity.
    """
    try:
        # Attempt a simple database query to check connectivity
        await db_session.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        db_status = f"failed: {e}"

    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "database_status": db_status,
        "rate_limiter_status": "active" if FastAPILimiter.redis else "inactive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# Example of a protected endpoint to demonstrate rate limiting
from datetime import datetime, timezone
@app.get("/protected-test", dependencies=[Depends(RateLimiter(times=5, seconds=60))], tags=["Test"])
async def protected_test():
    """
    An example endpoint to test rate limiting.
    Allows 5 requests per minute.
    """
    return {"message": "This is a protected endpoint, rate limited to 5 requests/minute."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG_MODE,
        log_level="info" if not settings.DEBUG_MODE else "debug"
    )