from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    """Base schema for user, containing common fields."""
    email: EmailStr = Field(..., example="user@example.com", description="User's email address.")

class UserCreate(UserBase):
    """Schema for creating a new user (registration)."""
    password: str = Field(..., min_length=8, max_length=64, example="StrongPassword123!", description="User's password.")

class UserLogin(UserBase):
    """Schema for user login."""
    password: str = Field(..., example="StrongPassword123!", description="User's password.")

class UserResponse(UserBase):
    """Schema for user data returned in API responses."""
    id: int = Field(..., example=1, description="Unique identifier for the user.")
    is_active: bool = Field(True, example=True, description="Indicates if the user account is active.")
    is_admin: bool = Field(False, example=False, description="Indicates if the user has administrative privileges.")
    created_at: datetime = Field(..., example="2023-01-01T12:00:00Z", description="Timestamp when the user was created.")
    updated_at: datetime = Field(..., example="2023-01-01T12:00:00Z", description="Timestamp when the user was last updated.")

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", description="JWT access token.")
    token_type: str = Field("bearer", example="bearer", description="Type of the token.")

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    email: Optional[str] = Field(None, example="user@example.com", description="Email of the user, used as subject in JWT.")