from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from auth_utils import decode_token
from schemas import TokenData
from core.exceptions import UnauthorizedException
from config import settings
from core.logging_config import setup_logging
import time
from collections import defaultdict

logger = setup_logging()

# OAuth2PasswordBearer for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises UnauthorizedException if token is invalid or missing.
    """
    try:
        token_data = decode_token(token)
        logger.debug(f"Current user authenticated: {token_data.email}")
        return token_data
    except UnauthorizedException as e:
        logger.warning(f"Authentication failed: {e.detail}")
        raise UnauthorizedException(detail="Could not validate credentials") from e

async def get_current_user_optional(token: str = Depends(oauth2_scheme)) -> TokenData | None:
    """
    Dependency to get the current authenticated user, but allows unauthenticated access.
    Returns None if token is invalid or missing.
    """
    try:
        token_data = decode_token(token)
        return token_data
    except UnauthorizedException:
        return None

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware per IP address.
    Not suitable for distributed systems without a shared cache (e.g., Redis).
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.limit = settings.RATE_LIMIT_PER_MINUTE # requests per minute

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # Remove requests older than 1 minute
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if current_time - t < 60
        ]

        if len(self.requests[client_ip]) >= self.limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"message": f"Rate limit exceeded. Max {self.limit} requests per minute."}
            )

        self.requests[client_ip].append(current_time)
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        
        return response