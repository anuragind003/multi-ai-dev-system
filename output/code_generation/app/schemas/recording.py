from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from app.models.recording import RecordingStatus

# Base schema for common attributes
class RecordingBase(BaseModel):
    lan_id: str = Field(..., min_length=5, max_length=50, description="Unique LAN ID for the VKYC recording.")

# Schema for creating a new recording (used internally by service)
class RecordingCreate(RecordingBase):
    file_path: Optional[str] = Field(None, description="Path to the recording file on NFS.")
    status: RecordingStatus = Field(RecordingStatus.PENDING, description="Current status of the recording.")
    error_message: Optional[str] = Field(None, description="Error message if processing failed.")

# Schema for response when retrieving a recording
class RecordingResponse(RecordingBase):
    id: int = Field(..., description="Unique identifier for the recording.")
    file_path: Optional[str] = Field(None, description="Path to the recording file on NFS.")
    upload_date: datetime = Field(..., description="Timestamp when the recording metadata was uploaded.")
    status: RecordingStatus = Field(..., description="Current status of the recording.")
    error_message: Optional[str] = Field(None, description="Error message if processing failed.")

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

# Schema for individual record processing result in bulk upload
class BulkUploadRecordDetail(BaseModel):
    lan_id: str = Field(..., description="LAN ID of the record.")
    status: RecordingStatus = Field(..., description="Processing status for this specific record.")
    message: Optional[str] = Field(None, description="Detailed message about the processing result.")

# Schema for the overall bulk upload response
class BulkUploadResponse(BaseModel):
    total_records: int = Field(..., description="Total number of records (LAN IDs) found in the uploaded file.")
    processed_records: int = Field(..., description="Number of records successfully processed and saved.")
    failed_records: int = Field(..., description="Number of records that failed processing.")
    details: List[BulkUploadRecordDetail] = Field(..., description="List of detailed results for each record.")
    message: str = Field(..., description="Overall message about the bulk upload operation.")