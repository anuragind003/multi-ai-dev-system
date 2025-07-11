from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from typing import Optional, List, Any
from models import VKYCRecordingStatus, UserRole

# --- General Schemas ---
class ErrorResponse(BaseModel):
    """Standard error response schema."""
    message: str = Field(..., description="A human-readable message describing the error.")
    code: str = Field(..., description="An internal error code for programmatic handling.")
    details: Optional[Any] = Field(None, description="Additional details about the error, e.g., validation errors.")

class HealthCheckResponse(BaseModel):
    """Schema for health check endpoint response."""
    status: str = Field(..., example="healthy")
    database_status: str = Field(..., example="connected")
    timestamp: datetime = Field(..., example="2023-10-27T10:00:00Z")
    version: str = Field(..., example="1.0.0")

# --- User Schemas (for Auth) ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, example="john.doe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    full_name: Optional[str] = Field(None, max_length=100, example="John Doe")
    role: UserRole = Field(UserRole.VIEWER, example=UserRole.VIEWER)
    is_active: bool = Field(True, example=True)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

class UserLogin(BaseModel):
    username: str = Field(..., example="john.doe")
    password: str = Field(..., example="securepassword123")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

# --- VKYC Recording Schemas ---
class VKYCRecordingBase(BaseModel):
    """Base schema for VKYC Recording, containing common fields."""
    lan_id: str = Field(..., min_length=5, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$", example="LAN123456789")
    recording_path: str = Field(..., min_length=10, max_length=255, example="/mnt/vkyc_recordings/2023/LAN123456789.mp4")
    recording_date: datetime = Field(..., example="2023-10-26T14:30:00Z")
    status: VKYCRecordingStatus = Field(VKYCRecordingStatus.PENDING, example=VKYCRecordingStatus.PENDING)
    uploaded_by: str = Field(..., min_length=3, max_length=100, example="admin_user")
    review_notes: Optional[str] = Field(None, max_length=500, example="Initial review: audio clear, video slightly blurry.")
    is_active: bool = Field(True, example=True)

    @validator('recording_date', pre=True)
    def parse_recording_date(cls, value):
        if isinstance(value, str):
            try:
                # Attempt to parse common ISO 8601 formats
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Invalid datetime format. Use ISO 8601 (e.g., '2023-10-26T14:30:00Z').")
        return value

class VKYCRecordingCreate(VKYCRecordingBase):
    """Schema for creating a new VKYC Recording."""
    # All fields from base are required for creation unless explicitly Optional
    pass

class VKYCRecordingUpdate(BaseModel):
    """Schema for updating an existing VKYC Recording."""
    lan_id: Optional[str] = Field(None, min_length=5, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$", example="LAN123456789")
    recording_path: Optional[str] = Field(None, min_length=10, max_length=255, example="/mnt/vkyc_recordings/2023/LAN123456789_v2.mp4")
    recording_date: Optional[datetime] = Field(None, example="2023-10-26T14:30:00Z")
    status: Optional[VKYCRecordingStatus] = Field(None, example=VKYCRecordingStatus.COMPLETED)
    uploaded_by: Optional[str] = Field(None, min_length=3, max_length=100, example="admin_user")
    review_notes: Optional[str] = Field(None, max_length=500, example="Final review: all checks passed.")
    is_active: Optional[bool] = Field(None, example=False)

    @validator('recording_date', pre=True)
    def parse_recording_date_update(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Invalid datetime format. Use ISO 8601 (e.g., '2023-10-26T14:30:00Z').")
        return value

class VKYCRecordingResponse(VKYCRecordingBase):
    """Schema for VKYC Recording response, including database-generated fields."""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-10-26T14:30:00.123456Z")
    updated_at: datetime = Field(..., example="2023-10-26T14:30:00.123456Z")

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic

class VKYCRecordingListResponse(BaseModel):
    """Schema for listing multiple VKYC Recordings with pagination info."""
    total: int = Field(..., example=100)
    page: int = Field(..., example=1)
    page_size: int = Field(..., example=10)
    items: List[VKYCRecordingResponse]