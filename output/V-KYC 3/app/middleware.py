from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from app.config import settings
from app.logger import logger
import time
from collections import defaultdict

# Simple in-memory rate limiter (for demonstration)
# In production, use a more robust solution like Redis (e.g., fastapi-limiter)
_request_counts = defaultdict(lambda: {'count': 0, 'last_reset_time': time.time()})
_RATE_LIMIT_WINDOW_SECONDS = 60 # 1 minute

class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add common security headers to all responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains", # HSTS
            "Referrer-Policy": "no-referrer-when-downgrade",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';",
            # Note: CSP can be complex and needs careful tuning for your frontend.
            # This is a strict example. 'unsafe-inline' for scripts/styles should be avoided if possible.
        }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self.headers.items():
            if header not in response.headers: # Don't overwrite if already set
                response.headers[header] = value
        logger.debug(f"Added security headers for request: {request.url}")
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware based on client IP.
    NOT suitable for distributed deployments without a shared state (e.g., Redis).
    For demonstration purposes only.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        if current_time - _request_counts[client_ip]['last_reset_time'] > _RATE_LIMIT_WINDOW_SECONDS:
            _request_counts[client_ip]['count'] = 0
            _request_counts[client_ip]['last_reset_time'] = current_time

        _request_counts[client_ip]['count'] += 1

        if _request_counts[client_ip]['count'] > self.rate_limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Max {self.rate_limit} requests per minute."},
                headers={"Retry-After": str(_RATE_LIMIT_WINDOW_SECONDS - (current_time - _request_counts[client_ip]['last_reset_time']))}
            )
        
        response = await call_next(request)
        return response