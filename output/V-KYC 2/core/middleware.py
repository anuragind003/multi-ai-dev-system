from fastapi import Request, Response
from starlette.types import ASGIApp
from utils.logger import setup_logging

logger = setup_logging()

async def add_security_headers(request: Request, call_next):
    """
    Middleware to add common security headers to all responses.
    """
    response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Referrer Policy
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    # Strict-Transport-Security (HSTS) - Only for HTTPS
    # For production, ensure your app is served over HTTPS and uncomment this.
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    # Content Security Policy (CSP) - Highly recommended for production, but complex to configure.
    # Example (very restrictive):
    # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self';"

    logger.debug(f"Security headers added for request: {request.url}")
    return response

# Note on Rate Limiting:
# A more robust rate limiting solution is provided by `slowapi` directly in `main.py`.
# This file can be used for other custom middleware if needed.