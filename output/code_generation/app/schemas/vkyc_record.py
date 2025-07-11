from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from typing import List, Optional

# --- Base Schemas ---
class VKYCRecordBase(BaseModel):
    """Base schema for VKYC record data."""
    lan_id: str = Field(..., min_length=5, max_length=50, pattern=r"^[A-Z0-9-]+$", description="Unique LAN ID for the VKYC case.")
    customer_name: str = Field(..., min_length=2, max_length=100, description="Name of the customer.")
    recording_date: datetime = Field(default_factory=datetime.utcnow, description="Date and time of the recording.")
    file_path: str = Field(..., min_length=5, max_length=255, description="Path to the recording file on NFS.")
    status: str = Field("completed", max_length=20, description="Status of the VKYC record (e.g., completed, pending, failed).")

    @validator('lan_id')
    def validate_lan_id_format(cls, v):
        if not v.isalnum() and '-' not in v:
            raise ValueError('LAN ID must be alphanumeric or contain hyphens.')
        return v

# --- Create/Update Schemas ---
class VKYCRecordCreate(VKYCRecordBase):
    """Schema for creating a new VKYC record."""
    # All fields from base are required for creation by default
    pass

class VKYCRecordUpdate(VKYCRecordBase):
    """Schema for updating an existing VKYC record."""
    lan_id: Optional[str] = Field(None, min_length=5, max_length=50, pattern=r"^[A-Z0-9-]+$", description="Unique LAN ID for the VKYC case.")
    customer_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Name of the customer.")
    recording_date: Optional[datetime] = Field(None, description="Date and time of the recording.")
    file_path: Optional[str] = Field(None, min_length=5, max_length=255, description="Path to the recording file on NFS.")
    status: Optional[str] = Field(None, max_length=20, description="Status of the VKYC record (e.g., completed, pending, failed).")
    is_active: Optional[bool] = Field(None, description="Whether the record is active.")

# --- Response Schemas ---
class VKYCRecordResponse(VKYCRecordBase):
    """Schema for returning VKYC record data."""
    id: int = Field(..., description="Unique ID of the VKYC record.")
    is_active: bool = Field(True, description="Whether the record is active.")
    created_at: datetime = Field(..., description="Timestamp when the record was created.")
    updated_at: datetime = Field(..., description="Timestamp when the record was last updated.")

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic

# --- Bulk Operations Schemas ---
class BulkUploadRequest(BaseModel):
    """Schema for bulk uploading LAN IDs from a file."""
    file_content: str = Field(..., description="Base64 encoded content of the CSV/TXT file containing LAN IDs.")
    file_name: str = Field(..., description="Name of the uploaded file (e.g., 'lan_ids.csv').")

class BulkUploadResult(BaseModel):
    """Schema for the result of a bulk upload operation."""
    total_records_processed: int = Field(..., description="Total number of LAN IDs found in the file.")
    successful_records: List[str] = Field(..., description="List of LAN IDs successfully processed.")
    failed_records: List[dict] = Field(..., description="List of LAN IDs that failed processing, with error details.")

class BulkDownloadRequest(BaseModel):
    """Schema for requesting a bulk download of VKYC records."""
    lan_ids: List[str] = Field(..., min_length=1, max_length=10, description="List of LAN IDs to download. Max 10 records per request.")

    @validator('lan_ids')
    def validate_lan_ids_format(cls, v):
        for lan_id in v:
            if not lan_id.isalnum() and '-' not in lan_id:
                raise ValueError(f"Invalid LAN ID format: {lan_id}. Must be alphanumeric or contain hyphens.")
        return v

class DownloadStatus(BaseModel):
    """Schema for the status of a single download item."""
    lan_id: str
    status: str = Field(..., description="Status of the download (e.g., 'success', 'not_found', 'error').")
    message: Optional[str] = Field(None, description="Additional message or error detail.")
    download_url: Optional[str] = Field(None, description="Temporary URL for successful downloads.")

class BulkDownloadResponse(BaseModel):
    """Schema for the response of a bulk download request."""
    request_id: str = Field(..., description="Unique ID for the bulk download request.")
    total_requested: int = Field(..., description="Total number of LAN IDs requested.")
    results: List[DownloadStatus] = Field(..., description="List of download statuses for each requested LAN ID.")