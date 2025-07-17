import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from config import settings
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis

log = logging.getLogger(__name__)

def setup_security_middleware(app: FastAPI):
    """
    Sets up various security-related middleware for the FastAPI application.
    Includes CORS, custom security headers, and rate limiting.
    """
    log.info("Setting up CORS middleware...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    log.info(f"CORS origins allowed: {settings.CORS_ORIGINS}")

    log.info("Adding custom security headers middleware...")
    app.add_middleware(SecurityHeadersMiddleware)

    log.info("Initializing Redis for Rate Limiting...")
    @app.on_event("startup")
    async def startup_event():
        redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis)
        log.info("FastAPI-Limiter initialized.")

    @app.on_event("shutdown")
    async def shutdown_event():
        if FastAPILimiter.redis:
            await FastAPILimiter.redis.close()
            log.info("FastAPI-Limiter Redis connection closed.")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add common security headers to all responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        # Content-Security-Policy can be complex and might need to be configured per-route or more dynamically
        # For a simple API, a restrictive CSP might break frontend integrations.
        # response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        return response