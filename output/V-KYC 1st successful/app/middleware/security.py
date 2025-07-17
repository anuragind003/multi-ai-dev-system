import time
from typing import Optional

import redis.asyncio as redis
from fastapi import Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging_config import logger

# Initialize Redis client for rate limiting
redis_client: Optional[redis.Redis] = None

async def connect_redis():
    """Connects to Redis for rate limiting."""
    global redis_client
    if settings.RATE_LIMIT_ENABLED:
        try:
            redis_client = redis.from_url(settings.RATE_LIMIT_REDIS_URL, decode_responses=True)
            await redis_client.ping()
            logger.info("Connected to Redis for rate limiting.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            redis_client = None # Ensure it's None if connection fails

async def disconnect_redis():
    """Disconnects from Redis."""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Disconnected from Redis.")

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API rate limiting based on IP address.
    Uses Redis to store request counts and timestamps.
    """
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED or redis_client is None:
            return await call_next(request)

        # Use client IP as key, fall back to a generic key if IP is not available
        client_ip = request.client.host if request.client else "unknown_ip"
        key = f"rate_limit:{client_ip}"
        current_time = int(time.time())

        # Use a Redis pipeline for atomic operations
        async with redis_client.pipeline() as pipe:
            pipe.lrem(key, 0, current_time - self.window_seconds) # Remove old timestamps
            pipe.lpush(key, current_time) # Add current timestamp
            pipe.ltrim(key, 0, self.requests_per_minute - 1) # Keep only the latest N timestamps
            pipe.expire(key, self.window_seconds) # Set expiration for the list

            timestamps = await pipe.execute()
            current_requests = len(timestamps[1]) # Length of the list after adding current timestamp

        if current_requests > self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute."},
                headers={"Retry-After": str(self.window_seconds)}
            )

        response = await call_next(request)
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add common security headers to responses.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        # Content-Security-Policy can be complex and might need to be configured per-route or more broadly
        # For a backend API, a restrictive CSP might not be necessary unless serving static content.
        # response.headers["Content-Security-Policy"] = "default-src 'self';"
        return response

def register_security_middleware(app):
    """Registers all security-related middleware with the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security middleware registered.")