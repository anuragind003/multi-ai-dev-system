import logging
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.database import SessionLocal
from app.services.file_parser import FileParserService

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication (if users were implemented)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token") # Adjust tokenUrl if needed

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get a SQLAlchemy database session.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("Database session closed.")

def get_file_parser_service(db: Session = Depends(get_db)) -> FileParserService:
    """
    Dependency to get an instance of FileParserService.
    Injects the database session into the service.
    """
    return FileParserService(db)

# Placeholder for user authentication dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency to get the current authenticated user.
    Requires a valid JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token payload missing 'sub' (username).")
            raise credentials_exception
        # In a real application, you would fetch the user from the database here
        # user = db.query(User).filter(User.username == username).first()
        # if user is None:
        #     logger.warning(f"User '{username}' not found in DB.")
        #     raise credentials_exception
        logger.info(f"User '{username}' authenticated successfully.")
        return {"username": username} # Return a simple dict for now
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during authentication.",
        ) from e