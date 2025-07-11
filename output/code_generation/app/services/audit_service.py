import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models import models
from app.schemas import schemas
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service layer for handling audit log operations.
    Encapsulates business logic and interacts with the database.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[dict] = None
    ) -> models.AuditLog:
        """
        Creates a new audit log entry.
        """
        db_audit_log = models.AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )
        self.db.add(db_audit_log)
        self.db.commit()
        self.db.refresh(db_audit_log)
        logger.info(f"Audit log created: User {user_id}, Action '{action}', Resource '{resource_type}:{resource_id}'")
        return db_audit_log

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[models.AuditLog]:
        """
        Retrieves audit logs with optional filtering.
        """
        query = self.db.query(models.AuditLog)

        if user_id:
            query = query.filter(models.AuditLog.user_id == user_id)
        if action:
            query = query.filter(models.AuditLog.action == action)
        if resource_type:
            query = query.filter(models.AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(models.AuditLog.resource_id == resource_id)
        if start_date:
            query = query.filter(models.AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(models.AuditLog.timestamp <= end_date)

        audit_logs = query.order_by(desc(models.AuditLog.timestamp)).offset(skip).limit(limit).all()
        logger.debug(f"Retrieved {len(audit_logs)} audit logs with filters.")
        return audit_logs

    def get_audit_log_by_id(self, log_id: int) -> models.AuditLog:
        """Retrieves a single audit log by its ID."""
        audit_log = self.db.query(models.AuditLog).filter(models.AuditLog.id == log_id).first()
        if not audit_log:
            raise NotFoundException(detail=f"Audit log with ID {log_id} not found.")
        return audit_log