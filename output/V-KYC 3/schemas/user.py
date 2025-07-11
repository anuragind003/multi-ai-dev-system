from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr = Field(..., example="john.doe@example.com")
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, example="John Doe")

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=50, example="StrongPassword123!")
    is_superuser: bool = False

class UserUpdate(UserBase):
    """Schema for updating an existing user."""
    email: Optional[EmailStr] = Field(None, example="john.doe.updated@example.com")
    password: Optional[str] = Field(None, min_length=8, max_length=50, example="NewStrongPassword123!")
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserInDB(UserBase):
    """Schema for user data as stored in the database (includes sensitive fields)."""
    id: int
    hashed_password: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

class UserResponse(UserBase):
    """Schema for user data returned in API responses (excludes sensitive fields)."""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    email: Optional[str] = None