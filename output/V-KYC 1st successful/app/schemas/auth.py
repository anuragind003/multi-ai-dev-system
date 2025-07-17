from pydantic import BaseModel, EmailStr
from typing import List, Optional

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    username: Optional[str] = None
    roles: List[str] = []

class UserBase(BaseModel):
    """Base schema for a user."""
    username: str
    email: Optional[EmailStr] = None

class UserCreate(UserBase):
    """Schema for creating a new user (e.g., for registration)."""
    password: str

class UserResponse(UserBase):
    """Schema for user data returned in API responses."""
    roles: List[str] = []
    is_active: bool = True

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

class UserLogin(BaseModel):
    """Schema for user login request."""
    username: str
    password: str