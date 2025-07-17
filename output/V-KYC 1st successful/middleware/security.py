from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add various security headers to responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.hsts_header = (
            f"max-age={settings.HSTS_MAX_AGE}"
            f"{'; includeSubDomains' if settings.HSTS_INCLUDE_SUBDOMAINS else ''}"
            f"{'; preload' if settings.HSTS_PRELOAD else ''}"
        )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # HTTP Strict Transport Security (HSTS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = self.hsts_header
        
        # X-Frame-Options
        response.headers["X-Frame-Options"] = settings.X_FRAME_OPTIONS
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = settings.X_CONTENT_TYPE_OPTIONS
        
        # Referrer-Policy
        response.headers["Referrer-Policy"] = settings.REFERRER_POLICY
        
        # X-XSS-Protection (often handled by CSP now, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content-Security-Policy (CSP) - More complex, often managed by a dedicated library or web server
        # For a simple API, a restrictive CSP might be:
        # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self';"
        
        return response

def setup_security_middleware(app: FastAPI):
    """
    Adds security headers middleware to the FastAPI application.
    """
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("SecurityHeadersMiddleware added.")

async def setup_rate_limiting(app: FastAPI):
    """
    Initializes FastAPI-Limiter with Redis backend.
    """
    if settings.RATE_LIMIT_ENABLED:
        try:
            redis_client = Redis.from_url(settings.RATE_LIMIT_REDIS_URL, encoding="utf-8", decode_responses=True)
            await FastAPILimiter.init(redis_client)
            logger.info(f"FastAPI-Limiter initialized with Redis at {settings.RATE_LIMIT_REDIS_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize FastAPI-Limiter: {e}", exc_info=True)
            logger.warning("Rate limiting will be disabled due to initialization failure.")
            settings.RATE_LIMIT_ENABLED = False # Disable if init fails
    else:
        logger.info("Rate limiting is disabled by configuration.")

# Expose limiter instance for use in endpoints
# This will be initialized in the lifespan event
limiter = FastAPILimiter