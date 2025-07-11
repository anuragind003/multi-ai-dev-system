import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class RecordingStatus(str, enum.Enum):
    """
    Enum for the status of a recording processing.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    INVALID_LAN_ID = "invalid_lan_id"
    NOT_FOUND_NFS = "not_found_nfs" # If the file isn't found on NFS after metadata upload

class Recording(Base):
    """
    SQLAlchemy model for VKYC Recording metadata.
    """
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, unique=True, index=True, nullable=False)
    file_path = Column(String, nullable=True) # Path on NFS server
    upload_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(Enum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False)
    error_message = Column(String, nullable=True) # To store details if processing failed

    def __repr__(self):
        return f"<Recording(id={self.id}, lan_id='{self.lan_id}', status='{self.status}')>"