from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from core.logger import logger

# OAuth2PasswordBearer for token extraction from Authorization header
# The tokenUrl parameter points to the endpoint where clients can obtain a token.
# This is used by FastAPI's OpenAPI documentation to describe the authentication flow.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class JWTBearer:
    """
    A custom dependency class to handle JWT token extraction and basic validation.
    It integrates with FastAPI's dependency injection system.
    """
    async def __call__(self, request: Request) -> str:
        """
        Extracts the JWT token from the Authorization header.
        Raises an HTTPException if the token is missing or malformed.
        """
        auth_header: Optional[str] = request.headers.get("Authorization")
        
        if not auth_header:
            logger.warning("Authorization header missing.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated: Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Authorization header malformed.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated: Invalid Authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = parts[1]
        logger.debug(f"Extracted token: {token[:10]}...") # Log first 10 chars for debugging
        return token