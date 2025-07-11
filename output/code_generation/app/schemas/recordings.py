from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, validator
from app.core.config import settings

class RecordingBase(BaseModel):
    """Base schema for VKYC Recording."""
    lan_id: str = Field(..., min_length=4, max_length=20, description="Unique LAN ID for the VKYC recording.")
    file_path: str = Field(..., description="Absolute path to the recording file on the NFS server.")
    recording_date: datetime = Field(..., description="Date and time when the recording was made.")
    status: str = Field("completed", description="Status of the recording (e.g., 'completed', 'failed', 'processing').")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes about the recording.")

    @validator('lan_id')
    def validate_lan_id_format(cls, v):
        if not v.isalnum(): # Example: only alphanumeric LAN IDs
            raise ValueError('LAN ID must be alphanumeric')
        return v

class RecordingCreate(RecordingBase):
    """Schema for creating a new VKYC Recording."""
    # All fields from RecordingBase are required for creation
    pass

class RecordingResponse(RecordingBase):
    """Schema for VKYC Recording response, including database-generated fields."""
    id: int = Field(..., description="Unique identifier for the recording.")
    created_at: datetime = Field(..., description="Timestamp when the record was created.")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the record was last updated.")

    class Config:
        from_attributes = True # Enable ORM mode for SQLAlchemy compatibility

class PaginationParams(BaseModel):
    """Schema for pagination query parameters."""
    page: int = Field(1, ge=1, description="Page number for pagination.")
    size: int = Field(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Number of items per page.")

class RecordingFilterParams(BaseModel):
    """Schema for filtering VKYC Recordings."""
    lan_id: Optional[str] = Field(None, description="Filter by LAN ID (partial match).")
    status: Optional[str] = Field(None, description="Filter by recording status.")
    start_date: Optional[datetime] = Field(None, description="Filter recordings from this date onwards.")
    end_date: Optional[datetime] = Field(None, description="Filter recordings up to this date.")

    @validator('start_date', 'end_date', pre=True)
    def parse_dates(cls, v):
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("Date must be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).")
        return v

class PaginatedRecordingsResponse(BaseModel):
    """Schema for paginated list of VKYC Recordings."""
    items: List[RecordingResponse] = Field(..., description="List of VKYC recording records.")
    total: int = Field(..., description="Total number of recording records available.")
    page: int = Field(..., description="Current page number.")
    size: int = Field(..., description="Number of items per page.")
    total_pages: int = Field(..., description="Total number of pages.")