import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.models import RecordingStatus, UserRole

# --- Generic Schemas ---
class MessageResponse(BaseModel):
    """Generic response schema for simple messages."""
    message: str

# --- User Schemas ---
class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=64, description="Password for the user")
    role: Optional[UserRole] = UserRole.USER

    @validator('password')
    def password_strength(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for char in v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

class UserResponse(UserBase):
    """Schema for returning user data."""
    id: int
    is_active: bool
    role: UserRole
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True # Enable ORM mode for SQLAlchemy models

# --- Token Schemas ---
class Token(BaseModel):
    """Schema for JWT access token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int # seconds until expiration
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    """Schema for data contained in JWT token."""
    email: Optional[str] = None
    user_id: Optional[int] = None
    roles: List[UserRole] = []

# --- Recording Schemas ---
class RecordingBase(BaseModel):
    """Base schema for recording data."""
    lan_id: str = Field(..., min_length=5, max_length=50, description="Loan Account Number ID")
    file_name: str = Field(..., min_length=5, max_length=255, description="Original file name of the recording")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes about the recording")

class RecordingCreate(RecordingBase):
    """Schema for creating a new recording."""
    file_path: str = Field(..., description="Absolute path to the recording file on NFS")

class RecordingUpdate(BaseModel):
    """Schema for updating an existing recording."""
    lan_id: Optional[str] = Field(None, min_length=5, max_length=50)
    file_name: Optional[str] = Field(None, min_length=5, max_length=255)
    file_path: Optional[str] = None
    status: Optional[RecordingStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)

class RecordingResponse(RecordingBase):
    """Schema for returning recording data."""
    id: int
    file_path: str
    upload_date: datetime.datetime
    status: RecordingStatus
    uploader_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class RecordingSearch(BaseModel):
    """Schema for searching recordings with filters."""
    lan_id: Optional[str] = None
    status: Optional[RecordingStatus] = None
    uploader_id: Optional[int] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    limit: int = Field(100, ge=1, le=500, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v and v < values['start_date']:
            raise ValueError('end_date cannot be before start_date')
        return v