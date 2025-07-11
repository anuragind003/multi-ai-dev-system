from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger
from config import get_settings
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add various security headers to responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
        return response

def setup_security_middleware(app: FastAPI):
    """
    Configures all security-related middleware for the FastAPI application.
    Includes CORS, custom security headers, and rate limiting.
    """
    settings = get_settings()

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    logger.info(f"CORS middleware configured for origins: {settings.CORS_ORIGINS}")

    # 2. Custom Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("SecurityHeadersMiddleware added.")

    # 3. Rate Limiting Middleware (requires Redis)
    # This setup assumes Redis is available. For a simple demo, it might be skipped
    # or a mock Redis client used. In production, ensure Redis is running.
    @app.on_event("startup")
    async def startup_rate_limiter():
        try:
            # Connect to Redis. Replace with your Redis connection string.
            # For local development, you might use `redis://localhost:6379`
            # For Docker, it might be `redis://redis:6379` if 'redis' is the service name.
            redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)
            await FastAPILimiter.init(redis_client)
            logger.info(f"Rate Limiter initialized with Redis. Default limit: {settings.RATE_LIMIT_PER_MINUTE}")
        except Exception as e:
            logger.error(f"Failed to initialize Rate Limiter with Redis: {e}. Rate limiting will be disabled.")
            # Optionally, you can set a flag or use a no-op limiter if Redis is critical.

    @app.on_event("shutdown")
    async def shutdown_rate_limiter():
        if FastAPILimiter._redis:
            await FastAPILimiter._redis.close()
            logger.info("Rate Limiter Redis connection closed.")