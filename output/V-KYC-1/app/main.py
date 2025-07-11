import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.api.v1 import auth, recordings, users
from app.config import settings
from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.middlewares import add_request_id_middleware
from app.database import engine, Base

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the application.
    """
    logger.info(f"Application '{settings.APP_NAME}' starting up...")

    # Initialize database tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (if not exist).")

    # Initialize FastAPI-Limiter
    # In a real production environment, use Redis for rate limiting
    # For this example, we'll use a simple in-memory backend (not suitable for distributed apps)
    # For production, replace with: await FastAPILimiter.init(redis_instance)
    # from redis.asyncio import Redis
    # redis_instance = Redis(host="redis", port=6379, db=0)
    # await FastAPILimiter.init(redis_instance)
    logger.warning("FastAPI-Limiter is using an in-memory backend. Use Redis for production!")
    await FastAPILimiter.init() # In-memory backend for demonstration

    yield

    logger.info(f"Application '{settings.APP_NAME}' shutting down...")
    # Clean up FastAPI-Limiter (if using Redis, close connection)
    await FastAPILimiter.close()


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for V-KYC Recording Portal. Manages recording metadata, user authentication, and secure file access.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    dependencies=[RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60)] # Global rate limit
)

# Add Request ID Middleware for better logging correlation
app.middleware("http")(add_request_id_middleware)

# Configure CORS
app.add_middleware(
    middleware_class=settings.CORS_MIDDLEWARE_CLASS,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic validation errors."""
    logger.warning(f"Validation error for request {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Validation Error"},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles FastAPI's HTTPException."""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": exc.detail},
    )

@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    """Handles custom UnauthorizedException."""
    logger.warning(f"Unauthorized access attempt: {exc.detail}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.detail, "message": "Authentication Required"},
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    """Handles custom ForbiddenException."""
    logger.warning(f"Forbidden access attempt: {exc.detail}")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail, "message": "Permission Denied"},
    )

@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    """Handles custom NotFoundException."""
    logger.warning(f"Resource not found: {exc.detail}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail, "message": "Resource Not Found"},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handles all other unhandled exceptions."""
    logger.exception(f"Unhandled exception for request {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred.", "message": "Internal Server Error"},
    )

# --- API Routers ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(recordings.router, prefix="/api/v1/recordings", tags=["Recordings"])

# --- Health Check Endpoint ---
@app.get("/health", summary="Health Check", response_model=dict)
async def health_check():
    """
    Checks the health of the API.
    """
    return {"status": "ok", "message": "API is running smoothly."}