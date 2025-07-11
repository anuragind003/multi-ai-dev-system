from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.schemas.bulk_download import DownloadStatus # Import the enum

class DownloadRequest(Base):
    """
    SQLAlchemy model for a bulk download request.
    Stores the overall request status and metadata.
    """
    __tablename__ = "download_requests"

    id = Column(String, primary_key=True, index=True) # UUID string
    status = Column(String, default=DownloadStatus.PENDING.value, nullable=False)
    requested_by = Column(String, nullable=False) # User who made the request
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    total_lan_ids = Column(Integer, nullable=False)

    # Relationship to individual file metadata
    files_metadata = relationship("FileMetadata", back_populates="download_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DownloadRequest(id='{self.id}', status='{self.status}')>"

class FileMetadata(Base):
    """
    SQLAlchemy model for individual file metadata within a bulk download request.
    """
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("download_requests.id"), nullable=False)
    lan_id = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    file_exists = Column(Boolean, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    last_modified_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)

    # Relationship back to the download request
    download_request = relationship("DownloadRequest", back_populates="files_metadata")

    def __repr__(self):
        return f"<FileMetadata(lan_id='{self.lan_id}', file_exists={self.file_exists})>"