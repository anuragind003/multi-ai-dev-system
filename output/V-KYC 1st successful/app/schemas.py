from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, HttpUrl

# --- User Schemas ---
class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=64)

class UserResponse(UserBase):
    """Schema for returning user data."""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True # For Pydantic v2, use from_attributes=True instead of orm_mode=True

class UserLogin(BaseModel):
    """Schema for user login credentials."""
    email: EmailStr
    password: str

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for data contained in JWT token."""
    email: Optional[str] = None
    roles: List[str] = [] # e.g., ["admin", "user", "process_manager"]

# --- Recording Schemas ---
class RecordingBase(BaseModel):
    """Base schema for recording data."""
    lan_id: str = Field(..., min_length=1, max_length=100, description="Unique LAN ID for the recording.")
    file_path: str = Field(..., description="Absolute path to the recording file on the NFS server.")
    file_name: str = Field(..., description="Original file name of the recording.")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Duration of the recording in seconds.")
    size_bytes: Optional[int] = Field(None, ge=0, description="Size of the recording file in bytes.")
    status: str = Field("available", description="Current status of the recording (e.g., available, processing, corrupted).")
    metadata_json: Optional[str] = Field(None, description="Additional metadata for the recording in JSON string format.")

class RecordingCreate(RecordingBase):
    """Schema for creating a new recording entry."""
    # No additional fields beyond RecordingBase for creation, but can be extended.
    pass

class RecordingResponse(RecordingBase):
    """Schema for returning recording details."""
    id: int
    upload_date: datetime

    class Config:
        from_attributes = True # For Pydantic v2, use from_attributes=True instead of orm_mode=True

# --- Error Schemas ---
class HTTPError(BaseModel):
    """Standard schema for HTTP error responses."""
    detail: str = Field(..., description="A detailed message about the error.")
    code: Optional[str] = Field(None, description="An optional error code for programmatic handling.")

    class Config:
        json_schema_extra = {
            "example": {"detail": "Item not found", "code": "NOT_FOUND"}
        }