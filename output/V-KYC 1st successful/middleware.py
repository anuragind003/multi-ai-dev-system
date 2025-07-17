from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from config import settings
import time
import logging

logger = logging.getLogger("security_testing_api")

def setup_cors_middleware(app: FastAPI):
    """
    Configures CORS (Cross-Origin Resource Sharing) middleware.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    logger.info(f"CORS middleware configured for origins: {settings.CORS_ORIGINS}")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add common security headers to responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains" # HSTS
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
        return response

def setup_security_headers_middleware(app: FastAPI):
    """
    Adds the SecurityHeadersMiddleware to the FastAPI application.
    """
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security Headers middleware added.")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log incoming requests and their processing time.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        return response

def setup_request_logging_middleware(app: FastAPI):
    """
    Adds the RequestLoggingMiddleware to the FastAPI application.
    """
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request Logging middleware added.")

# Rate Limiting setup (requires Redis)
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis as AsyncRedis
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan_rate_limiter(app: FastAPI):
    """
    Context manager for FastAPI-Limiter lifecycle.
    Initializes Redis connection on startup and closes on shutdown.
    """
    if settings.REDIS_URL:
        try:
            redis_connection = AsyncRedis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            await FastAPILimiter.init(redis_connection)
            logger.info("FastAPI-Limiter initialized with Redis.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}")
            # Optionally, raise an exception or disable rate limiting if Redis is critical
    else:
        logger.warning("REDIS_URL not set. Rate limiting will be disabled.")
    yield
    if settings.REDIS_URL and FastAPILimiter.redis:
        await FastAPILimiter.redis.close()
        logger.info("FastAPI-Limiter Redis connection closed.")