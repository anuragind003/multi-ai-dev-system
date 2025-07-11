from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator, constr

from db.models import BulkRequestStatusEnum, LanIdProcessingStatusEnum

# --- Input Schemas ---

class LanIdInput(BaseModel):
    """
    Schema for a single LAN ID input in a bulk request.
    """
    lan_id: constr(min_length=1, max_length=50, strip_whitespace=True) = Field(
        ..., example="LAN123456", description="Unique identifier for a LAN."
    )

class BulkRequestCreate(BaseModel):
    """
    Schema for creating a new bulk request.
    """
    lan_ids: List[LanIdInput] = Field(
        ..., 
        min_items=1, 
        max_items=10, # As per context, limit to 10 records per bulk download
        description="List of LAN IDs to be processed in bulk."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        example={"filename": "bulk_upload_20231027.csv", "source_ip": "192.168.1.1"},
        description="Optional metadata associated with the bulk request."
    )

    @validator('lan_ids')
    def validate_unique_lan_ids(cls, v):
        """Ensures all LAN IDs in the list are unique."""
        if len(v) != len(set(item.lan_id for item in v)):
            raise ValueError("All LAN IDs in the request must be unique.")
        return v

# --- Output Schemas ---

class LanIdStatusResponse(BaseModel):
    """
    Schema for the status of an individual LAN ID within a bulk request.
    """
    lan_id: str = Field(..., example="LAN123456", description="Unique identifier for a LAN.")
    status: LanIdProcessingStatusEnum = Field(..., example=LanIdProcessingStatusEnum.PENDING, description="Processing status of the LAN ID.")
    message: Optional[str] = Field(None, example="File not found on NFS server.", description="Detailed message if processing failed.")
    processed_at: datetime = Field(..., example="2023-10-27T10:30:00.000Z", description="Timestamp when this LAN ID's status was last updated.")

    class Config:
        orm_mode = True # Enable ORM mode for automatic conversion from SQLAlchemy models

class BulkRequestResponse(BaseModel):
    """
    Schema for the full response of a bulk request, including all LAN ID statuses.
    """
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000", description="Unique ID of the bulk request.")
    user_id: UUID = Field(..., example="a1b2c3d4-e5f6-7890-1234-567890abcdef", description="ID of the user who initiated the request.")
    status: BulkRequestStatusEnum = Field(..., example=BulkRequestStatusEnum.PROCESSING, description="Overall status of the bulk request.")
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        example={"filename": "bulk_upload_20231027.csv", "total_lan_ids": 5},
        description="Metadata associated with the bulk request."
    )
    created_at: datetime = Field(..., example="2023-10-27T10:00:00.000Z", description="Timestamp when the bulk request was created.")
    updated_at: datetime = Field(..., example="2023-10-27T10:35:00.000Z", description="Timestamp when the bulk request was last updated.")
    lan_id_statuses: List[LanIdStatusResponse] = Field(
        ..., 
        description="List of individual LAN ID statuses within this bulk request."
    )

    class Config:
        orm_mode = True # Enable ORM mode for automatic conversion from SQLAlchemy models