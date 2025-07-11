from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from schemas import AuditLogResponse, UserResponse
from services import AuditLogService
from utils.dependencies import get_db, get_audit_log_service, get_current_user
from utils.errors import ForbiddenException
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/", response_model=List[AuditLogResponse], summary="Get Audit Logs", description="Retrieves a list of audit log entries. (Admin only)")
async def get_audit_logs(
    skip: int = Query(0, ge=0, description="Number of items to skip (for pagination)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return (for pagination)"),
    current_user: UserResponse = Depends(get_current_user),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
):
    """
    Retrieves a paginated list of audit log entries.
    Requires admin privileges.
    """
    if not current_user.is_admin:
        raise ForbiddenException("Only administrators can view audit logs.")
    
    try:
        logs = audit_log_service.get_audit_logs(skip=skip, limit=limit)
        logger.info(f"User {current_user.username} retrieved {len(logs)} audit logs (skip={skip}, limit={limit}).")
        return logs
    except Exception as e:
        logger.error(f"Error retrieving audit logs for user {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve audit logs.")