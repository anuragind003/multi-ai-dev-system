import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from db.models import BulkRequest, LanIdStatus, BulkRequestStatusEnum, LanIdProcessingStatusEnum
from schemas.bulk_request import BulkRequestCreate, BulkRequestResponse, LanIdStatusResponse
from core.exceptions import NotFoundException, InternalServerError
from utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

class BulkRequestService:
    """
    Service layer for handling bulk request business logic.
    Encapsulates database interactions and external service calls (simulated NFS).
    """
    def __init__(self, db: Session):
        self.db = db

    async def create_bulk_request(self, request_data: BulkRequestCreate, user_id: UUID) -> BulkRequestResponse:
        """
        Creates a new bulk request and initializes the status for each LAN ID.
        Starts a background task to process the LAN IDs.
        """
        try:
            # Create the main bulk request entry
            bulk_request = BulkRequest(
                user_id=user_id,
                status=BulkRequestStatusEnum.PENDING,
                metadata=request_data.metadata or {}
            )
            # Add total_lan_ids to metadata for convenience
            bulk_request.metadata["total_lan_ids"] = len(request_data.lan_ids)
            
            self.db.add(bulk_request)
            self.db.flush() # Flush to get the bulk_request.id

            # Create individual LAN ID status entries
            lan_id_statuses = []
            for lan_id_input in request_data.lan_ids:
                lan_status = LanIdStatus(
                    bulk_request_id=bulk_request.id,
                    lan_id=lan_id_input.lan_id,
                    status=LanIdProcessingStatusEnum.PENDING,
                    message="Queued for processing"
                )
                lan_id_statuses.append(lan_status)
            
            self.db.add_all(lan_id_statuses)
            self.db.commit()
            self.db.refresh(bulk_request)

            logger.info(f"Bulk request {bulk_request.id} created by user {user_id} with {len(request_data.lan_ids)} LAN IDs.")

            # Start background processing (non-blocking)
            # In a real app, this would be a message queue (e.g., Celery, RabbitMQ)
            # or a dedicated background worker. For this example, we use asyncio.create_task.
            asyncio.create_task(self._process_lan_ids_in_background(bulk_request.id))

            return BulkRequestResponse.from_orm(bulk_request)
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating bulk request: {e}")
            raise InternalServerError(detail="Failed to create bulk request due to a database error.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating bulk request: {e}")
            raise InternalServerError(detail="An unexpected error occurred while creating the bulk request.")

    async def get_bulk_request_by_id(self, request_id: UUID) -> BulkRequestResponse:
        """
        Retrieves a bulk request and its associated LAN ID statuses.
        """
        try:
            bulk_request = self.db.query(BulkRequest).filter(BulkRequest.id == request_id).first()
            if not bulk_request:
                raise NotFoundException(detail=f"Bulk request with ID '{request_id}' not found.")
            
            # Eagerly load lan_id_statuses for the response
            # This avoids N+1 query problem if not already loaded by relationship
            bulk_request.lan_id_statuses # Accessing it triggers load if not already loaded

            return BulkRequestResponse.from_orm(bulk_request)
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving bulk request {request_id}: {e}")
            raise InternalServerError(detail="Failed to retrieve bulk request due to a database error.")
        except NotFoundException:
            raise # Re-raise specific exception
        except Exception as e:
            logger.error(f"Unexpected error retrieving bulk request {request_id}: {e}")
            raise InternalServerError(detail="An unexpected error occurred while retrieving the bulk request.")

    async def _process_lan_ids_in_background(self, bulk_request_id: UUID):
        """
        Simulates background processing of LAN IDs.
        In a real scenario, this would involve calling an external service (e.g., NFS).
        Updates the status of each LAN ID and the overall bulk request.
        """
        # Create a new session for the background task to avoid conflicts with request session
        # This is crucial for long-running background tasks
        from db.database import SessionLocal
        db_background = SessionLocal()
        try:
            bulk_request = db_background.query(BulkRequest).filter(BulkRequest.id == bulk_request_id).first()
            if not bulk_request:
                logger.error(f"Background processing failed: Bulk request {bulk_request_id} not found.")
                return

            bulk_request.status = BulkRequestStatusEnum.PROCESSING
            db_background.commit()
            db_background.refresh(bulk_request)
            logger.info(f"Bulk request {bulk_request_id} status updated to PROCESSING.")

            lan_id_statuses = db_background.query(LanIdStatus).filter(LanIdStatus.bulk_request_id == bulk_request_id).all()
            
            all_successful = True
            for lan_status in lan_id_statuses:
                # Simulate external call to NFS or VKYC system
                await asyncio.sleep(0.5) # Simulate network latency/processing time

                # Simulate success/failure based on LAN ID pattern or random chance
                if "FAIL" in lan_status.lan_id.upper() or datetime.now().microsecond % 10 < 2: # ~20% failure rate
                    lan_status.status = LanIdProcessingStatusEnum.FAILED
                    lan_status.message = f"Simulated: Failed to retrieve data for {lan_status.lan_id} from NFS."
                    all_successful = False
                else:
                    lan_status.status = LanIdProcessingStatusEnum.SUCCESS
                    lan_status.message = f"Simulated: Data for {lan_status.lan_id} retrieved successfully from NFS."
                
                lan_status.processed_at = datetime.utcnow()
                db_background.add(lan_status)
                db_background.commit() # Commit each LAN ID status update
                db_background.refresh(lan_status)
                logger.debug(f"LAN ID {lan_status.lan_id} status updated to {lan_status.status}.")

            # Update overall bulk request status
            bulk_request.status = BulkRequestStatusEnum.COMPLETED if all_successful else BulkRequestStatusEnum.FAILED
            db_background.add(bulk_request)
            db_background.commit()
            db_background.refresh(bulk_request)
            logger.info(f"Bulk request {bulk_request_id} processing finished. Final status: {bulk_request.status}.")

        except SQLAlchemyError as e:
            db_background.rollback()
            logger.error(f"Database error during background processing for request {bulk_request_id}: {e}")
            # Attempt to set bulk request status to FAILED if possible
            try:
                bulk_request = db_background.query(BulkRequest).filter(BulkRequest.id == bulk_request_id).first()
                if bulk_request:
                    bulk_request.status = BulkRequestStatusEnum.FAILED
                    db_background.commit()
            except Exception as rollback_e:
                logger.error(f"Failed to update bulk request {bulk_request_id} status to FAILED after error: {rollback_e}")
        except Exception as e:
            logger.error(f"Unexpected error during background processing for request {bulk_request_id}: {e}")
            # Attempt to set bulk request status to FAILED if possible
            try:
                bulk_request = db_background.query(BulkRequest).filter(BulkRequest.id == bulk_request_id).first()
                if bulk_request:
                    bulk_request.status = BulkRequestStatusEnum.FAILED
                    db_background.commit()
            except Exception as rollback_e:
                logger.error(f"Failed to update bulk request {bulk_request_id} status to FAILED after error: {rollback_e}")
        finally:
            db_background.close()
            logger.debug(f"Background DB session for request {bulk_request_id} closed.")