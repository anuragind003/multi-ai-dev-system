from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, status
from collections import defaultdict
import time

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add various security headers to responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains", # HSTS
            "Referrer-Policy": "no-referrer-when-downgrade",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()", # Example, adjust as needed
        }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self.headers.items():
            response.headers[header] = value
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic in-memory rate limiting middleware.
    NOT suitable for distributed environments without a shared store (e.g., Redis).
    For production, consider `fastapi-limiter` with Redis.
    """
    def __init__(self, app: ASGIApp, limit: int = 100, window: int = 60):
        super().__init__(app)
        self.limit = limit  # Max requests
        self.window = window  # Time window in seconds
        self.requests = defaultdict(list) # Stores timestamps of requests per IP

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Remove old requests outside the window
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > current_time - self.window
        ]

        if len(self.requests[client_ip]) >= self.limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content="Too Many Requests",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(self.window)}
            )
        
        self.requests[client_ip].append(current_time)
        response = await call_next(request)
        return response