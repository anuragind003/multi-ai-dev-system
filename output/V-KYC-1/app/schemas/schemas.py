from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional
from datetime import datetime, date
from app.models.models import RecordingStatus

# --- User Schemas ---

class UserBase(BaseModel):
    """Base schema for user data."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username for the user")
    email: EmailStr = Field(..., description="Unique email address of the user")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name of the user")

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="Password for the user account")
    roles: List[str] = Field(["user"], description="List of roles assigned to the user (e.g., ['user', 'admin'])")

    @validator('roles')
    def validate_roles(cls, v):
        allowed_roles = ["user", "admin"]
        if not all(role in allowed_roles for role in v):
            raise ValueError(f"Invalid role(s) provided. Allowed roles are: {', '.join(allowed_roles)}")
        return v

class UserUpdate(UserBase):
    """Schema for updating an existing user."""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Unique username for the user")
    email: Optional[EmailStr] = Field(None, description="Unique email address of the user")
    password: Optional[str] = Field(None, min_length=8, description="New password for the user account")
    is_active: Optional[bool] = Field(None, description="Whether the user account is active")
    roles: Optional[List[str]] = Field(None, description="List of roles assigned to the user")

    @validator('roles')
    def validate_roles(cls, v):
        if v is not None:
            allowed_roles = ["user", "admin"]
            if not all(role in allowed_roles for role in v):
                raise ValueError(f"Invalid role(s) provided. Allowed roles are: {', '.join(allowed_roles)}")
        return v

class UserResponse(UserBase):
    """Schema for returning user data (excludes password hash)."""
    id: int = Field(..., description="Unique identifier of the user")
    is_active: bool = Field(..., description="Whether the user account is active")
    roles: List[str] = Field(..., description="List of roles assigned to the user")
    created_at: datetime = Field(..., description="Timestamp of user creation")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of last user update")

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

# --- Token Schemas ---

class Token(BaseModel):
    """Schema for JWT access token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Type of the token (always 'bearer')")

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    username: Optional[str] = Field(None, description="Username encoded in the token")
    roles: List[str] = Field([], description="Roles encoded in the token")

# --- Recording Schemas ---

class RecordingBase(BaseModel):
    """Base schema for recording data."""
    lan_id: str = Field(..., min_length=5, max_length=50, description="Unique LAN ID for the recording")
    customer_name: str = Field(..., min_length=3, max_length=100, description="Name of the customer associated with the recording")
    recording_date: datetime = Field(..., description="Date and time when the recording was made (ISO 8601 format)")
    file_path: str = Field(..., min_length=5, max_length=255, description="Relative path to the recording file on the NFS server (e.g., '2023/01/LAN12345.mp4')")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Duration of the recording in seconds")
    status: RecordingStatus = Field(RecordingStatus.PENDING, description="Approval status of the recording (Pending, Approved, Rejected, Archived)")
    notes: Optional[str] = Field(None, max_length=500, description="Any additional notes or comments about the recording")

    @validator('file_path')
    def validate_file_path(cls, v):
        # Basic sanitization: prevent path traversal
        if '..' in v or v.startswith('/') or v.startswith('\\'):
            raise ValueError("File path cannot contain '..' or start with '/' or '\\'. Must be a relative path.")
        return v

class RecordingCreate(RecordingBase):
    """Schema for creating a new recording metadata entry."""
    # All fields from RecordingBase are required for creation
    pass

class RecordingUpdate(BaseModel):
    """Schema for updating an existing recording metadata entry."""
    lan_id: Optional[str] = Field(None, min_length=5, max_length=50, description="Unique LAN ID for the recording")
    customer_name: Optional[str] = Field(None, min_length=3, max_length=100, description="Name of the customer associated with the recording")
    recording_date: Optional[datetime] = Field(None, description="Date and time when the recording was made (ISO 8601 format)")
    file_path: Optional[str] = Field(None, min_length=5, max_length=255, description="Relative path to the recording file on the NFS server")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Duration of the recording in seconds")
    status: Optional[RecordingStatus] = Field(None, description="Approval status of the recording")
    notes: Optional[str] = Field(None, max_length=500, description="Any additional notes or comments about the recording")

    @validator('file_path')
    def validate_file_path(cls, v):
        if v is not None:
            if '..' in v or v.startswith('/') or v.startswith('\\'):
                raise ValueError("File path cannot contain '..' or start with '/' or '\\'. Must be a relative path.")
        return v

class RecordingResponse(RecordingBase):
    """Schema for returning recording data."""
    id: int = Field(..., description="Unique identifier of the recording")
    uploaded_by_user_id: Optional[int] = Field(None, description="ID of the user who uploaded this recording's metadata")
    created_at: datetime = Field(..., description="Timestamp of recording metadata creation")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of last recording metadata update")

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

class RecordingFilter(BaseModel):
    """Schema for filtering recordings."""
    lan_id: Optional[str] = Field(None, description="Filter by LAN ID (partial match)")
    customer_name: Optional[str] = Field(None, description="Filter by customer name (partial match)")
    start_date: Optional[str] = Field(None, description="Filter by recording date (YYYY-MM-DD) from")
    end_date: Optional[str] = Field(None, description="Filter by recording date (YYYY-MM-DD) to")
    status: Optional[RecordingStatus] = Field(None, description="Filter by approval status")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format.")
        return v