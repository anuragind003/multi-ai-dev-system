### FILE: api/v1/endpoints/audit_logs.py
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db_session
from services.audit_log_service import AuditLogService
from schemas import AuditLogResponse
from middleware.security import get_current_user, require_role
from utils.logger import logger

router = APIRouter()

@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="Retrieve audit logs",
    description="Fetches a list of audit log entries, with optional filtering and pagination. Requires 'auditor' or 'admin' role.",
    tags=["Audit Logs"]
)
async def get_audit_logs_endpoint(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type (e.g., BULK_DOWNLOAD)"),
    status: Optional[str] = Query(None, description="Filter by log status (e.g., SUCCESS, FAILED)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    current_user: dict = Depends(require_role("auditor")), # Enforce auditor or admin role
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint to retrieve audit logs.
    """
    logger.info(f"User '{current_user['username']}' requesting audit logs with filters: user_id={user_id}, action={action}, status={status}")
    audit_service = AuditLogService(db)
    logs = await audit_service.get_audit_logs(user_id=user_id, action=action, status=status, skip=skip, limit=limit)
    return logs

@router.get(
    "/audit-logs/{log_id}",
    response_model=AuditLogResponse,
    summary="Retrieve a single audit log by ID",
    description="Fetches a specific audit log entry by its ID. Requires 'auditor' or 'admin' role.",
    tags=["Audit Logs"]
)
async def get_audit_log_by_id_endpoint(
    log_id: int,
    current_user: dict = Depends(require_role("auditor")),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Endpoint to retrieve a single audit log by ID.
    """
    logger.info(f"User '{current_user['username']}' requesting audit log with ID: {log_id}")
    audit_service = AuditLogService(db)
    log = await audit_service.get_audit_log_by_id(log_id)
    return log