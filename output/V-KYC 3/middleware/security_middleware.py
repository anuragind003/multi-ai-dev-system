import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from fastapi import Request

from config import settings

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add various security headers to all responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        logger.info("SecurityHeadersMiddleware initialized.")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # X-Frame-Options: Prevents clickjacking attacks
        response.headers["X-Frame-Options"] = settings.X_FRAME_OPTIONS

        # X-Content-Type-Options: Prevents MIME-sniffing attacks
        response.headers["X-Content-Type-Options"] = settings.X_CONTENT_TYPE_OPTIONS

        # X-XSS-Protection: Enables the XSS filter in browsers
        response.headers["X-XSS-Protection"] = settings.X_XSS_PROTECTION

        # Strict-Transport-Security: Enforces HTTPS for future requests
        # Only add if running over HTTPS (e.g., in production behind a load balancer)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = settings.STRICT_TRANSPORT_SECURITY

        # Referrer-Policy: Controls how much referrer information is sent with requests
        response.headers["Referrer-Policy"] = settings.REFERRER_POLICY

        # Content-Security-Policy: (More complex, often configured via web server or more specific middleware)
        # Example: response.headers["Content-Security-Policy"] = "default-src 'self';"

        # Permissions-Policy (formerly Feature-Policy): Controls browser features
        # Example: response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"

        logger.debug(f"Security headers added for request to {request.url.path}")
        return response

# Note: This middleware needs to be added to the FastAPI app in main.py
# Example in main.py:
# from middleware.security_middleware import SecurityHeadersMiddleware
# app.add_middleware(SecurityHeadersMiddleware)