from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger
from config import settings
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis
import time

def setup_cors_middleware(app: ASGIApp):
    """Configures CORS middleware for the FastAPI application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS middleware configured for origins: {settings.CORS_ORIGINS}")

async def setup_rate_limiting(app: ASGIApp):
    """Initializes FastAPI-Limiter for rate limiting."""
    try:
        redis_connection = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)
        await FastAPILimiter.init(redis_connection, prefix="fastapi-limiter", strategy=settings.RATE_LIMIT_STRATEGY)
        logger.info(f"Rate limiting initialized with Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis for rate limiting: {e}. Rate limiting will be disabled.")
        # Optionally, you can set a dummy limiter or raise an exception to prevent app startup
        # For production, you might want to ensure Redis is available.

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging incoming requests and outgoing responses.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request details
        logger.info(f"Incoming Request: {request.method} {request.url.path} from {request.client.host}")

        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Log response details
        logger.info(f"Outgoing Response: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        
        return response

def setup_logging_middleware(app: ASGIApp):
    """Adds the custom logging middleware to the FastAPI application."""
    app.add_middleware(LoggingMiddleware)
    logger.info("Logging middleware added.")

# Dependency for applying rate limits to specific routes
rate_limit_dependency = RateLimiter(times=settings.RATE_LIMIT_REQUESTS_PER_MINUTE, minutes=1)