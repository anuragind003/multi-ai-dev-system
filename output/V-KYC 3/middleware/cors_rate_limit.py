from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis.asyncio import Redis as AIORedis
from typing import Callable

from config import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

def setup_cors_middleware(app: FastAPI):
    """
    Configures CORS (Cross-Origin Resource Sharing) middleware.
    Allows specified origins to make requests to the API.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"], # Allows all methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"], # Allows all headers
    )
    logger.info(f"CORS middleware configured for origins: {settings.CORS_ORIGINS}")

async def setup_rate_limiter(app: FastAPI):
    """
    Initializes the FastAPI-Limiter with a Redis backend.
    This function should be called on application startup.
    """
    try:
        # Assuming Redis is accessible at 'redis://localhost:6379' or configured via env
        # For production, use a proper Redis connection string from config
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_instance = AIORedis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(
            redis_instance,
            prefix=settings.RATE_LIMIT_KEY_PREFIX
        )
        logger.info("FastAPI-Limiter initialized with Redis.")
    except Exception as e:
        logger.error(f"Failed to initialize FastAPI-Limiter: {e}")
        # Depending on criticality, you might want to raise an exception or just log and continue without rate limiting

def get_rate_limiter_dependency() -> Callable:
    """
    Returns a dependency that applies a rate limit to an endpoint.
    Uses the configured rate limit from settings.
    """
    return RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60)

# Custom middleware for security headers (optional, but good practice)
async def add_security_headers(request: Request, call_next: Callable):
    """
    Adds common security headers to responses.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    logger.debug("Security headers added to response.")
    return response