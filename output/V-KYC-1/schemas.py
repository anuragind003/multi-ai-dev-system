from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from models import UserRole

# --- Health Check Schema ---
class HealthCheckResponse(BaseModel):
    status: str
    message: str

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$",
                          examples=["john_doe"], description="Unique username for the user.")
    email: EmailStr = Field(..., examples=["john.doe@example.com"], description="Unique email address of the user.")
    role: UserRole = Field(UserRole.USER, description="Role of the user (admin, manager, user).")
    is_active: bool = Field(True, description="Whether the user account is active.")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128,
                          description="Password for the user. Must be at least 8 characters long.")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$",
                                    description="New username for the user.")
    email: Optional[EmailStr] = Field(None, description="New email address of the user.")
    password: Optional[str] = Field(None, min_length=8, max_length=128,
                                    description="New password for the user.")
    role: Optional[UserRole] = Field(None, description="New role for the user.")
    is_active: Optional[bool] = Field(None, description="New active status for the user.")

class UserResponse(UserBase):
    id: int = Field(..., description="Unique identifier of the user.")
    created_at: datetime = Field(..., description="Timestamp when the user account was created.")
    updated_at: datetime = Field(..., description="Timestamp when the user account was last updated.")

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode for Pydantic

# --- Authentication Schemas ---
class LoginRequest(BaseModel):
    username: str = Field(..., description="Username for login.")
    password: str = Field(..., description="Password for login.")

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Type of the token.")

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[UserRole] = [] # List of roles for the user