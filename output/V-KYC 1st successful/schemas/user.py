from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base schema for user data."""
    username: str = Field(..., min_length=3, max_length=50, example="john.doe")
    email: Optional[EmailStr] = Field(None, example="john.doe@example.com")
    full_name: Optional[str] = Field(None, max_length=100, example="John Doe")
    is_active: bool = Field(True, example=True)
    is_admin: bool = Field(False, example=False)
    role: str = Field("user", example="user", pattern="^(user|tl|process_manager|admin)$")

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, example="SecureP@ssw0rd")

class UserUpdate(UserBase):
    """Schema for updating an existing user."""
    username: Optional[str] = None
    password: Optional[str] = None # Only for password change, not for general update
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    role: Optional[str] = None

class UserRead(UserBase):
    """Schema for reading user data, includes database-generated fields."""
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2023-10-26T10:00:00.123456Z")
    updated_at: datetime = Field(..., example="2023-10-26T10:00:00.123456Z")

    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field("bearer", example="bearer")

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    username: Optional[str] = None
    roles: list[str] = [] # List of roles for authorization