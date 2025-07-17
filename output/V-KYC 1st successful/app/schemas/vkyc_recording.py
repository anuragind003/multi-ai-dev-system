from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List

class VKYCRecordingBase(BaseModel):
    """Base schema for VKYC recording metadata."""
    lan_id: str = Field(..., min_length=5, max_length=50, description="Unique LAN ID for the VKYC recording.")
    recording_date: datetime = Field(..., description="Date and time when the recording was made.")
    file_path: str = Field(..., min_length=10, max_length=255, description="Full path to the recording file on the NFS server.")
    status: str = Field("PENDING", max_length=20, description="Current status of the recording (e.g., PENDING, PROCESSED, FAILED).")

    @validator('lan_id')
    def validate_lan_id_format(cls, v):
        # Example: LAN ID must be alphanumeric and start with 'LAN'
        if not v.isalnum() or not v.startswith('LAN'):
            raise ValueError('LAN ID must be alphanumeric and start with "LAN"')
        return v

class VKYCRecordingCreate(VKYCRecordingBase):
    """Schema for creating a new VKYC recording entry."""
    # uploaded_by is typically derived from the authenticated user, not provided by client
    pass

class VKYCRecordingUpdate(BaseModel):
    """Schema for updating an existing VKYC recording entry."""
    lan_id: Optional[str] = Field(None, min_length=5, max_length=50, description="Unique LAN ID for the VKYC recording.")
    recording_date: Optional[datetime] = Field(None, description="Date and time when the recording was made.")
    file_path: Optional[str] = Field(None, min_length=10, max_length=255, description="Full path to the recording file on the NFS server.")
    status: Optional[str] = Field(None, max_length=20, description="Current status of the recording (e.g., PENDING, PROCESSED, FAILED).")

    @validator('lan_id')
    def validate_lan_id_format(cls, v):
        if v is not None and (not v.isalnum() or not v.startswith('LAN')):
            raise ValueError('LAN ID must be alphanumeric and start with "LAN"')
        return v

class VKYCRecordingResponse(VKYCRecordingBase):
    """Schema for VKYC recording data returned in API responses."""
    id: int = Field(..., description="Unique identifier for the recording entry in the database.")
    uploaded_by: str = Field(..., description="User who uploaded/ingested the metadata.")
    created_at: datetime = Field(..., description="Timestamp when the record was created.")
    updated_at: datetime = Field(..., description="Timestamp when the record was last updated.")

    class Config:
        from_attributes = True # Enable ORM mode for SQLAlchemy compatibility

class CSVUploadRequest(BaseModel):
    """Schema for CSV file upload request."""
    # The actual file content will be handled by FastAPI's UploadFile
    # This schema is more for conceptual documentation or if there were other fields
    pass

class CSVUploadResult(BaseModel):
    """Schema for CSV upload processing result."""
    total_records: int = Field(..., description="Total records attempted to process from CSV.")
    successful_ingestions: int = Field(..., description="Number of records successfully ingested/updated.")
    failed_ingestions: int = Field(..., description="Number of records that failed ingestion.")
    errors: List[str] = Field([], description="List of error messages for failed records.")

class VKYCRecordingListResponse(BaseModel):
    """Schema for a list of VKYC recordings with pagination info."""
    total: int = Field(..., description="Total number of records matching the query.")
    page: int = Field(..., description="Current page number.")
    page_size: int = Field(..., description="Number of records per page.")
    items: List[VKYCRecordingResponse] = Field(..., description="List of VKYC recording metadata.")