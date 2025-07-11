from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.config import settings
import time
import logging
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

logger = logging.getLogger(__name__)

def setup_middleware(app: FastAPI):
    """
    Sets up all necessary middleware for the FastAPI application.
    """
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    logger.info(f"CORS middleware configured for origins: {settings.CORS_ORIGINS}")

    # Security Headers Middleware
    app.add_middleware(SecureHeadersMiddleware)
    logger.info("Security Headers middleware added.")

    # Request Logging Middleware (optional, for detailed request logs)
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request Logging middleware added.")

    # Rate Limiting is initialized in main.py's startup event due to async Redis client

class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add common security headers to responses.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log incoming requests and their processing time.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request: {request.method} {request.url.path} - "
                    f"Status: {response.status_code} - "
                    f"Processing Time: {process_time:.4f}s")
        return response

# Rate Limiting setup (to be called in app startup)
async def init_rate_limiter(app: FastAPI):
    """Initializes the FastAPI-Limiter with a Redis backend."""
    if settings.RATE_LIMIT_ENABLED:
        # Using a simple in-memory Redis for demonstration.
        # In production, use a proper Redis instance.
        # For local testing without Redis, you can use `FastAPILimiter.init()` without args
        # or mock redis.asyncio.Redis.
        try:
            redis_client = redis.Redis(host="localhost", port=6379, db=0, encoding="utf-8", decode_responses=True)
            await FastAPILimiter.init(redis_client)
            logger.info("FastAPI-Limiter initialized with Redis.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}. Rate limiting disabled.")
            settings.RATE_LIMIT_ENABLED = False # Disable if Redis connection fails
    else:
        logger.info("Rate Limiting is disabled via settings.")

# Dependency for rate limiting specific endpoints
# Usage: @app.get("/some-endpoint", dependencies=[Depends(rate_limit_dependency)])
rate_limit_dependency = RateLimiter(times=settings.RATE_LIMIT_REQUESTS_PER_MINUTE, seconds=60)