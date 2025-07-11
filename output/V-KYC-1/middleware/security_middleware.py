from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from fastapi import Request, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from config import settings
from core.logging_config import setup_logging

logger = setup_logging()

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add various security headers to responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.headers = {
            "Strict-Transport-Security": f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains",
            "X-Frame-Options": settings.X_FRAME_OPTIONS,
            "X-Content-Type-Options": settings.X_CONTENT_TYPE_OPTIONS,
            "X-XSS-Protection": settings.X_XSS_PROTECTION,
            "Referrer-Policy": settings.REFERRER_POLICY,
            "Content-Security-Policy": settings.CONTENT_SECURITY_POLICY,
            "Permissions-Policy": "geolocation=(), microphone=()", # Example: disable geolocation and microphone
        }
        logger.info("SecurityHeadersMiddleware initialized.")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self.headers.items():
            response.headers[header] = value
        logger.debug(f"Added security headers for request: {request.url.path}")
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for global rate limiting using fastapi-limiter.
    Requires Redis connection.
    """
    _redis_client: Optional[redis.Redis] = None

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        logger.info("RateLimitMiddleware initialized.")

    @classmethod
    async def init_redis_connection(cls):
        """Initializes the Redis connection for rate limiting."""
        try:
            cls._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                encoding="utf-8",
                decode_responses=True
            )
            await FastAPILimiter.init(cls._redis_client)
            logger.info(f"FastAPILimiter initialized with Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {e}", exc_info=True)
            # In a production environment, you might want to make this a critical failure
            # or implement a fallback mechanism.

    @classmethod
    async def close_redis_connection(cls):
        """Closes the Redis connection."""
        if cls._redis_client:
            await cls._redis_client.close()
            logger.info("Redis connection for FastAPILimiter closed.")

    async def dispatch(self, request: Request, call_next):
        if not self._redis_client:
            logger.warning("Rate limiting is not active: Redis client not initialized.")
            return await call_next(request)

        # Apply a default rate limit to all requests
        # For more granular control, use @limiter.limit() decorator on specific routes
        # or a dependency in the router.
        try:
            # This is a simplified global application. For production,
            # you'd typically use `FastAPILimiter.depends()` in route dependencies.
            # Here, we simulate the check.
            # A more robust way is to apply it directly to the router or specific endpoints.
            # For a global middleware, you might need to manually check or use a custom dependency.
            # This example shows the setup, but actual enforcement is usually via `Depends`.
            # For a true global middleware, you'd need to integrate `fastapi-limiter`'s
            # internal logic more deeply or use a custom `RateLimiter` instance.
            # For simplicity, we'll assume the `FastAPILimiter` is set up and
            # its `depends` function will be used in routes.
            # The middleware itself doesn't enforce the limit directly without a dependency.
            # This middleware primarily serves to initialize and manage the Redis client.
            pass
        except Exception as e:
            logger.error(f"Rate limiting error: {e}", exc_info=True)
            # Decide how to handle rate limiting errors (e.g., allow request or block)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"}
            )
        
        response = await call_next(request)
        return response

# Example of how to use RateLimiter dependency in a route (not in this file, but for context)
# from fastapi import APIRouter, Depends
# from fastapi_limiter.depends import RateLimiter
#
# router = APIRouter()
#
# @router.get("/protected", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
# async def protected_route():
#     return {"message": "This route is rate-limited to 10 requests per minute."}