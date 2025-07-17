import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from fastapi import Request, status
from collections import defaultdict
import time

from config import settings

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware:
    """
    Middleware to add various security headers to responses.
    Also includes a very basic in-memory rate limiting.
    For production, a more robust rate limiter (e.g., using Redis) is recommended.
    """
    def __init__(self, app: ASGIApp):
        self.app = app
        self.request_counts = defaultdict(lambda: []) # Stores timestamps of requests per IP

    async def __call__(self, request: Request, call_next):
        # --- Rate Limiting (Basic In-Memory) ---
        client_ip = request.client.host
        current_time = time.time()

        # Clean up old requests
        self.request_counts[client_ip] = [
            t for t in self.request_counts[client_ip] if current_time - t < 60
        ]

        if len(self.request_counts[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                "Too Many Requests", status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )
        self.request_counts[client_ip].append(current_time)

        # --- Process Request and Get Response ---
        response = await call_next(request)

        # --- Add Security Headers ---
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self';"
        # Note: CSP can be complex and needs to be tailored to your frontend.
        # 'unsafe-inline' for script/style is generally discouraged but sometimes necessary for dev/specific libraries.

        return response