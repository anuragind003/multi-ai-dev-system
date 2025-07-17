from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional

class RecordingBase(BaseModel):
    """Base schema for recording data."""
    lan_id: str = Field(..., min_length=1, max_length=50, example="VKYC-2023-001")
    file_path: str = Field(..., min_length=1, max_length=255, example="/mnt/nfs/recordings/2023/VKYC-2023-001.mp4")
    file_name: str = Field(..., min_length=1, max_length=100, example="VKYC-2023-001.mp4")
    file_size_bytes: Optional[int] = Field(None, ge=0, example=1024 * 1024 * 50) # 50 MB
    recording_date: Optional[datetime] = Field(None, example="2023-10-26T10:00:00Z")
    status: str = Field("available", example="available", pattern="^(available|archived|deleted)$")

class RecordingCreate(RecordingBase):
    """Schema for creating a new recording entry."""
    # All fields from RecordingBase are required for creation unless specified otherwise
    pass

class RecordingUpdate(RecordingBase):
    """Schema for updating an existing recording entry."""
    lan_id: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    recording_date: Optional[datetime] = None
    status: Optional[str] = None

class RecordingRead(RecordingBase):
    """Schema for reading recording data, includes database-generated fields."""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-10-26T10:00:00.123456Z")
    updated_at: datetime = Field(..., example="2023-10-26T10:00:00.123456Z")

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic