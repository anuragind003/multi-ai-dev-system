### FILE: app/services/audit_log_service.py
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse, BulkDownloadRequest, BulkDownloadResult
from app.core.exceptions import NotFoundException, InvalidInputException, ServiceUnavailableException
from app.utils.file_handler import NFSFileHandler # Import the simulated NFS handler

logger = logging.getLogger(__name__)

class AuditLogService:
    """
    Service layer for managing audit logs and handling bulk recording downloads.
    Encapsulates business logic and interacts with the database and file system.
    """
    def __init__(self, db_session: AsyncSession, file_handler: NFSFileHandler):
        self.db = db_session
        self.file_handler = file_handler

    async def create_log(self, log_data: AuditLogCreate) -> AuditLogResponse:
        """
        Creates a new audit log entry in the database.
        """
        try:
            db_log = AuditLog(**log_data.model_dump())
            self.db.add(db_log)
            await self.db.commit()
            await self.db.refresh(db_log)
            logger.info(f"Audit log created: Action='{db_log.action}', User='{db_log.user_id}', Resource='{db_log.resource_id}'")
            return AuditLogResponse.model_validate(db_log)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            raise ServiceUnavailableException(detail="Failed to record audit log due to database error.")

    async def get_logs(self, skip: int = 0, limit: int = 100, user_id: Optional[str] = None, action: Optional[str] = None) -> List[AuditLogResponse]:
        """
        Retrieves audit logs from the database with optional filtering and pagination.
        """
        query = select(AuditLog).offset(skip).limit(limit).order_by(desc(AuditLog.timestamp))
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)

        try:
            result = await self.db.execute(query)
            logs = result.scalars().all()
            return [AuditLogResponse.model_validate(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}", exc_info=True)
            raise ServiceUnavailableException(detail="Failed to retrieve audit logs due to database error.")

    async def record_bulk_download(
        self,
        request_data: BulkDownloadRequest,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handles the logic for recording a bulk recording download.
        This involves checking file existence and logging the outcome for each LAN ID.
        """
        if not request_data.lan_ids:
            raise InvalidInputException(detail="No LAN IDs provided for bulk download.")
        if len(request_data.lan_ids) > 10:
            raise InvalidInputException(detail="Maximum 10 LAN IDs allowed per bulk download request.")

        results: List[BulkDownloadResult] = []
        successful_downloads = []
        failed_downloads = []

        for lan_id in request_data.lan_ids:
            lan_id = lan_id.strip() # Sanitize input
            if not lan_id:
                results.append(BulkDownloadResult(lan_id="", status="FAILED", message="Empty LAN ID provided."))
                failed_downloads.append({"lan_id": "", "reason": "Empty LAN ID"})
                continue

            try:
                # Simulate checking file existence on NFS
                file_exists = await self.file_handler.check_file_exists(lan_id)
                if file_exists:
                    file_path = await self.file_handler.get_file_path(lan_id)
                    results.append(BulkDownloadResult(lan_id=lan_id, status="SUCCESS", message="File found and ready for download.", file_path=file_path))
                    successful_downloads.append(lan_id)
                else:
                    results.append(BulkDownloadResult(lan_id=lan_id, status="NOT_FOUND", message="Recording not found on NFS."))
                    failed_downloads.append({"lan_id": lan_id, "reason": "Not found"})
            except Exception as e:
                logger.error(f"Error checking file for LAN ID {lan_id}: {e}", exc_info=True)
                results.append(BulkDownloadResult(lan_id=lan_id, status="FAILED", message=f"Internal error checking file: {e}"))
                failed_downloads.append({"lan_id": lan_id, "reason": f"Internal error: {e}"})

        overall_status = "COMPLETED"
        if successful_downloads and failed_downloads:
            overall_status = "PARTIAL_SUCCESS"
        elif not successful_downloads and failed_downloads:
            overall_status = "FAILED"

        # Create audit log entry for the bulk download
        audit_log_details = {
            "requested_lan_ids": request_data.lan_ids,
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "overall_status": overall_status
        }
        audit_log_data = AuditLogCreate(
            user_id=user_id,
            action="BULK_DOWNLOAD",
            resource_type="RECORDING_BATCH",
            resource_id=None, # No single resource ID for a batch
            details=audit_log_details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        created_log = await self.create_log(audit_log_data)

        return {
            "overall_status": overall_status,
            "results": results,
            "audit_log_id": created_log.id
        }