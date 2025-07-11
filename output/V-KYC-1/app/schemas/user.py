from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Base Pydantic models for common attributes
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr

# Schema for creating a new user (request body)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

# Schema for user login (request body)
class UserLogin(BaseModel):
    username_or_email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)

# Schema for user response (what's returned to the client)
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True # Enable ORM mode for SQLAlchemy compatibility

# Schema for JWT token response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Schema for token data (payload inside JWT)
class TokenData(BaseModel):
    username: Optional[str] = None