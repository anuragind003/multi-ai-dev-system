import logging
from typing import List, Union

from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_secure_headers import SecureHeadersMiddleware
import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)

async def setup_rate_limiting(app: FastAPI):
    """
    Initializes FastAPI-Limiter with Redis.
    """
    try:
        redis_instance = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_instance)
        logger.info("FastAPI-Limiter initialized with Redis.")
    except Exception as e:
        logger.error(f"Failed to initialize FastAPI-Limiter: {e}")
        # Optionally, raise the exception or handle it gracefully if rate limiting is critical
        # For now, we'll just log and continue without rate limiting
        FastAPILimiter.redis = None # Ensure redis is None if init fails

def setup_secure_headers(app: FastAPI):
    """
    Adds SecureHeadersMiddleware to the FastAPI application.
    This middleware automatically adds various security headers.
    """
    app.add_middleware(SecureHeadersMiddleware)
    logger.info("SecureHeadersMiddleware added.")