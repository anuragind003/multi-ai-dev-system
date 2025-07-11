import logging
import redis.asyncio as redis
from fastapi import FastAPI, Request, status
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from core.exceptions import RateLimitExceededException
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def init_rate_limiter(app: FastAPI):
    """
    Initializes the FastAPI-Limiter with Redis.
    This function should be called on application startup.
    """
    try:
        # Use redis.asyncio for async Redis client
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_client)
        logger.info("FastAPI-Limiter initialized with Redis.")
    except Exception as e:
        logger.error(f"Failed to initialize FastAPI-Limiter: {e}", exc_info=True)
        # Depending on criticality, you might want to raise an exception or
        # disable rate limiting if Redis is unavailable.
        # For production, this should be a critical error.

async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededException):
    """
    Custom exception handler for RateLimitExceededException.
    Returns a 429 Too Many Requests response.
    """
    logger.warning(f"Rate limit exceeded for IP: {request.client.host}")
    return await FastAPILimiter.http_exception_handler(request, exc)

# Dependency for applying rate limits to specific endpoints
# Usage: Depends(rate_limit_dependency)
rate_limit_dependency = RateLimiter(times=settings.RATE_LIMIT_CALLS, seconds=settings.RATE_LIMIT_PERIOD)