from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

class DownloadStatus(str, Enum):
    """
    Enum for the status of a bulk download request.
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"

class FileMetadataSchema(BaseModel):
    """
    Schema for individual file metadata.
    """
    lan_id: str = Field(..., description="LAN ID associated with the VKYC recording.")
    file_path: str = Field(..., description="Full path to the recording file on the NFS server.")
    file_exists: bool = Field(..., description="Indicates if the file was found on the NFS server.")
    file_size_bytes: Optional[int] = Field(None, description="Size of the file in bytes, if found.")
    last_modified_at: Optional[datetime] = Field(None, description="Last modification timestamp of the file, if found.")
    error_message: Optional[str] = Field(None, description="Error message if file processing failed for this LAN ID.")

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

class BulkDownloadRequest(BaseModel):
    """
    Schema for a bulk download request, containing a list of LAN IDs.
    """
    lan_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=10, # Limit to 10 records per bulk download as per context
        description="List of LAN IDs for which to fetch VKYC recording metadata and check existence. Max 10."
    )

    @validator('lan_ids')
    def validate_lan_ids(cls, v):
        """
        Validates that LAN IDs are alphanumeric and unique.
        """
        if not all(isinstance(item, str) and item.isalnum() for item in v):
            raise ValueError("All LAN IDs must be alphanumeric strings.")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate LAN IDs are not allowed in a single request.")
        return v

class BulkDownloadResponse(BaseModel):
    """
    Schema for the response of a bulk download request.
    """
    request_id: str = Field(..., description="Unique identifier for the bulk download request.")
    status: DownloadStatus = Field(..., description="Current status of the bulk download request.")
    requested_at: datetime = Field(..., description="Timestamp when the request was initiated.")
    processed_at: Optional[datetime] = Field(None, description="Timestamp when the request finished processing.")
    total_lan_ids: int = Field(..., description="Total number of LAN IDs in the request.")
    processed_files: List[FileMetadataSchema] = Field(..., description="List of processed file metadata.")
    
    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility