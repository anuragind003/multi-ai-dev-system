from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from starlette.requests import Request
import time
from collections import defaultdict
from app.utils.logger import get_logger
from app.schemas.common import APIResponse
from app.core.exceptions import CustomHTTPException

logger = get_logger(__name__)

class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add various security headers to responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains", # HSTS
            "Referrer-Policy": "no-referrer-when-downgrade",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';",
        }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self.headers.items():
            if header not in response.headers: # Don't overwrite if already set
                response.headers[header] = value
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware based on IP address.
    Not suitable for distributed systems without a shared cache (e.g., Redis).
    """
    def __init__(self, app: ASGIApp, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests = defaultdict(list) # Stores timestamps of requests per IP

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean up old requests (older than 1 minute)
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > current_time - 60
        ]

        if len(self.requests[client_ip]) >= self.calls_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content=APIResponse(
                    success=False,
                    message="Too Many Requests",
                    data={"detail": f"Rate limit exceeded. Max {self.calls_per_minute} requests per minute."}
                ).model_dump(mode='json'),
                headers={"Retry-After": "60"}
            )
        
        self.requests[client_ip].append(current_time)
        response = await call_next(request)
        return response