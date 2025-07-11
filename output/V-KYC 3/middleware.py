from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from config import get_settings
from logger import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

settings = get_settings()

# Initialize the rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])

def setup_middleware(app: FastAPI):
    """
    Configures and adds all necessary middleware to the FastAPI application.
    Includes CORS, security headers, and rate limiting.
    """
    logger.info("Setting up middleware...")

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    logger.info(f"CORS configured for origins: {settings.CORS_ORIGINS}")

    # Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("SecurityHeadersMiddleware added.")

    # Rate Limiting Middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info(f"Rate limiting configured: {settings.RATE_LIMIT_PER_MINUTE} requests/minute.")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add common security headers to all responses.
    Helps mitigate common web vulnerabilities.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self';"
        return response