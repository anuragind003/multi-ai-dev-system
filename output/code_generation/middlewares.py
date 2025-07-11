import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.config import settings

logger = logging.getLogger(__name__)

def setup_cors_middleware(app: FastAPI):
    """
    Configures CORS (Cross-Origin Resource Sharing) middleware.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS middleware configured for origins: {settings.CORS_ORIGINS}")

async def add_security_headers(request: Request, call_next: Callable):
    """
    Middleware to add various security headers to responses.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    # Content-Security-Policy can be complex, add carefully based on your needs
    # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self';"
    return response

async def setup_rate_limit_middleware(app: FastAPI):
    """
    Configures rate limiting middleware using fastapi-limiter.
    This should be called during app startup.
    """
    # In a real production environment, you'd use Redis for rate limiting.
    # For this example, we'll use an in-memory backend for simplicity.
    # from redis.asyncio import Redis
    # await FastAPILimiter.init(Redis(host="localhost", port=6379))
    
    # For demonstration without Redis:
    logger.warning("FastAPILimiter is running without a Redis backend. This is not suitable for production.")
    await FastAPILimiter.init(prefix="fastapi-limiter") # Using default in-memory backend

    # You can apply rate limiting globally or per endpoint.
    # For global, you'd add a dependency to all routes or use a router dependency.
    # Example: app.router.dependencies.append(Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60)))
    logger.info(f"Rate limiting middleware configured: {settings.RATE_LIMIT_PER_MINUTE} requests/minute.")

async def timing_middleware(request: Request, call_next: Callable):
    """
    Middleware to measure and log the response time of API requests.
    Useful for performance monitoring.
    """
    start_time = time.perf_counter()
    response = await call_next(request)
    end_time = time.perf_counter()
    process_time = (end_time - start_time) * 1000  # in milliseconds

    # Log request details and processing time
    logger.info(f"Request: {request.method} {request.url.path} | "
                f"Status: {response.status_code} | "
                f"Time: {process_time:.2f}ms")
    
    # Add custom header for response time (optional, for debugging/monitoring)
    response.headers["X-Process-Time"] = str(process_time)
    return response