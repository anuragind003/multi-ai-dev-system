from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from typing import Optional, List, Dict, Any

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    roles: str = Field("user", description="Comma-separated roles, e.g., 'user,admin'")
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = []

# --- Recording Schemas ---
class RecordingBase(BaseModel):
    lan_id: str = Field(..., min_length=5, max_length=100, description="Unique LAN ID for the recording")
    file_path: str = Field(..., min_length=5, max_length=255, description="Relative path to the recording file on NFS")
    status: str = Field("available", description="Status of the recording (e.g., available, archived)")

class RecordingCreate(RecordingBase):
    pass # No extra fields for creation beyond base

class RecordingResponse(RecordingBase):
    id: int
    upload_date: datetime

    class Config:
        from_attributes = True

# --- Audit Log Schemas ---
class AuditLogBase(BaseModel):
    action: str = Field(..., min_length=3, max_length=100, description="Action performed (e.g., 'download_recording')")
    resource_type: str = Field(..., min_length=3, max_length=50, description="Type of resource acted upon (e.g., 'recording', 'user')")
    resource_id: Optional[int] = Field(None, description="ID of the resource acted upon")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context in JSON format (e.g., IP, user_agent)")

class AuditLogCreate(AuditLogBase):
    user_id: int = Field(..., description="ID of the user who performed the action")

class AuditLogResponse(AuditLogBase):
    id: int
    user_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Health Check Schema ---
class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Overall health status")
    database: str = Field(..., description="Database connection status")
    nfs_access: str = Field(..., description="NFS access simulation status")
    timestamp: datetime