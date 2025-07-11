from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db
from services import AuthService, RecordingService, AuditLogService
from middleware.auth import get_current_user
from schemas import UserResponse

# --- Database Session Dependency ---
# get_db is already defined in database.py, but we can re-export it here
# for consistency if all dependencies are managed from this file.
# from database import get_db

# --- Service Dependencies ---
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Provides an instance of AuthService with a database session."""
    return AuthService(db)

def get_recording_service(db: Session = Depends(get_db)) -> RecordingService:
    """Provides an instance of RecordingService with a database session."""
    return RecordingService(db)

def get_audit_log_service(db: Session = Depends(get_db)) -> AuditLogService:
    """Provides an instance of AuditLogService with a database session."""
    return AuditLogService(db)

# --- Authentication Dependency ---
# get_current_user is already defined in middleware/auth.py, but re-export for consistency
# from middleware.auth import get_current_user