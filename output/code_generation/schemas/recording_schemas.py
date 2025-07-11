from pydantic import BaseModel, Field, validator
from typing import List, Optional
import datetime
import re

class RecordingBase(BaseModel):
    """Base schema for recording data."""
    lan_id: str = Field(..., min_length=1, max_length=50, description="Unique identifier for the VKYC case.")
    file_path: str = Field(..., min_length=1, max_length=255, description="Absolute path to the recording file on NFS.")
    recorded_at: datetime.datetime = Field(..., description="Timestamp when the recording was made.")

    @validator('lan_id')
    def validate_lan_id_format(cls, v):
        """Validate LAN ID format (e.g., alphanumeric, no special chars)."""
        if not re.fullmatch(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('LAN ID must be alphanumeric, hyphens, or underscores only.')
        return v

class RecordingCreate(RecordingBase):
    """Schema for creating a new recording entry."""
    pass

class RecordingResponse(RecordingBase):
    """Schema for returning recording data from the API."""
    id: int = Field(..., description="Database ID of the recording.")
    status: str = Field(..., description="Current status of the recording (e.g., available, processing).")
    created_at: datetime.datetime = Field(..., description="Timestamp when the record was created in DB.")
    updated_at: datetime.datetime = Field(..., description="Timestamp when the record was last updated in DB.")
    metadata_json: Optional[str] = Field(None, description="Optional JSON string for additional metadata.")

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

class BulkDownloadRequest(BaseModel):
    """Schema for the bulk download request body."""
    lan_ids: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=10, # Enforce the 10 recordings at a time limit
        description="List of LAN IDs for recordings to download. Max 10 items."
    )

    @validator('lan_ids')
    def validate_lan_ids_content(cls, v):
        """Validate each LAN ID in the list."""
        if not v:
            raise ValueError('LAN ID list cannot be empty.')
        
        # Validate format of each LAN ID
        for lan_id in v:
            if not re.fullmatch(r'^[a-zA-Z0-9_-]+$', lan_id):
                raise ValueError(f"Invalid LAN ID format found: '{lan_id}'. Must be alphanumeric, hyphens, or underscores only.")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError('Duplicate LAN IDs found in the request.')
        
        return v

class ErrorResponse(BaseModel):
    """Generic error response schema."""
    detail: str = Field(..., description="A detailed error message.")
    errors: Optional[List[dict]] = Field(None, description="Optional list of specific validation errors.")