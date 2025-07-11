from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# --- Authentication & Authorization Schemas ---
class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    email: Optional[str] = None
    scopes: List[str] = [] # Not directly used for RBAC, but good practice for OAuth2 scopes

class LoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="securepassword")

class RoleBase(BaseModel):
    """Base schema for a Role."""
    name: str = Field(..., min_length=3, max_length=50, example="auditor")
    description: Optional[str] = Field(None, max_length=255, example="Can view and download recordings")

class RoleCreate(RoleBase):
    """Schema for creating a new Role."""
    pass

class RoleResponse(RoleBase):
    """Schema for returning Role details."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PermissionBase(BaseModel):
    """Base schema for a Permission."""
    name: str = Field(..., min_length=3, max_length=100, example="recording:read")
    description: Optional[str] = Field(None, max_length=255, example="View recording metadata")

class PermissionResponse(PermissionBase):
    """Schema for returning Permission details."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- User Schemas ---
class UserBase(BaseModel):
    """Base schema for a User."""
    email: EmailStr = Field(..., example="john.doe@example.com")
    first_name: Optional[str] = Field(None, max_length=100, example="John")
    last_name: Optional[str] = Field(None, max_length=100, example="Doe")
    is_active: bool = True

class UserCreate(UserBase):
    """Schema for creating a new User."""
    password: str = Field(..., min_length=6, example="securepassword123")
    role_id: int = Field(..., example=2, description="ID of the role assigned to the user (e.g., 1 for admin, 2 for auditor)")

class UserUpdate(UserBase):
    """Schema for updating an existing User."""
    email: Optional[EmailStr] = Field(None, example="john.doe.new@example.com")
    password: Optional[str] = Field(None, min_length=6, example="newsecurepassword")
    role_id: Optional[int] = Field(None, example=1)

class UserResponse(UserBase):
    """Schema for returning User details."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    role: RoleResponse # Nested role information

    class Config:
        from_attributes = True

# --- Recording Schemas ---
class RecordingBase(BaseModel):
    """Base schema for a Recording."""
    lan_id: str = Field(..., min_length=1, max_length=100, example="LAN12345")
    file_name: str = Field(..., min_length=1, max_length=255, example="vkyc_call_20231026_LAN12345.mp4")
    file_path: str = Field(..., min_length=1, max_length=500, example="/nfs/recordings/2023/vkyc_call_20231026_LAN12345.mp4")
    file_size_bytes: Optional[int] = Field(None, ge=0, example=1024 * 1024 * 50) # 50 MB
    recording_date: Optional[datetime] = Field(None, example="2023-10-26T10:00:00Z")
    status: str = Field("available", max_length=50, example="available")
    metadata_json: Optional[str] = Field(None, example='{"customer_name": "Alice Smith", "duration_seconds": 300}')

class RecordingCreate(RecordingBase):
    """Schema for creating a new Recording."""
    # uploader_id will be derived from the authenticated user
    pass

class RecordingUpdate(BaseModel):
    """Schema for updating an existing Recording."""
    lan_id: Optional[str] = Field(None, min_length=1, max_length=100, example="LAN12345_updated")
    file_name: Optional[str] = Field(None, min_length=1, max_length=255, example="vkyc_call_20231026_LAN12345_v2.mp4")
    file_path: Optional[str] = Field(None, min_length=1, max_length=500, example="/nfs/recordings/2023/vkyc_call_20231026_LAN12345_v2.mp4")
    file_size_bytes: Optional[int] = Field(None, ge=0, example=1024 * 1024 * 60)
    recording_date: Optional[datetime] = Field(None, example="2023-10-26T10:15:00Z")
    status: Optional[str] = Field(None, max_length=50, example="archived")
    metadata_json: Optional[str] = Field(None, example='{"customer_name": "Alice Smith", "duration_seconds": 300, "notes": "Updated metadata"}')

class RecordingResponse(RecordingBase):
    """Schema for returning Recording details."""
    id: int
    upload_date: datetime
    uploader_id: int
    uploader: UserResponse # Nested uploader information (can be simplified if full user details not needed)

    class Config:
        from_attributes = True

# --- Bulk Request Schemas ---
class BulkRequestBase(BaseModel):
    """Base schema for a Bulk Request."""
    request_type: str = Field(..., max_length=50, example="download")
    status: str = Field("pending", max_length=50, example="pending")
    parameters_json: Optional[str] = Field(None, example='{"lan_ids": ["LAN123", "LAN456"]}')
    result_json: Optional[str] = Field(None, example='{"success_count": 2, "failed_count": 0}')

class BulkRequestCreate(BulkRequestBase):
    """Schema for creating a new Bulk Request."""
    # requested_by_id will be derived from the authenticated user
    pass

class BulkRequestResponse(BulkRequestBase):
    """Schema for returning Bulk Request details."""
    id: int
    requested_at: datetime
    completed_at: Optional[datetime] = None
    requested_by_id: int
    requester: UserResponse # Nested requester information

    class Config:
        from_attributes = True

# --- Error Response Schema ---
class ErrorResponse(BaseModel):
    """Generic error response schema."""
    detail: str = Field(..., example="Resource not found.")
    message: str = Field(..., example="Not Found")