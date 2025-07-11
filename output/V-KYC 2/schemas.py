from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from models import UserRole

class Token(BaseModel):
    """Pydantic model for JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Pydantic model for data contained in JWT token."""
    username: Optional[str] = None
    roles: list[UserRole] = Field(default_factory=list) # Store roles as list of enum values

class UserBase(BaseModel):
    """Base Pydantic model for user data."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")

class UserCreate(UserBase):
    """Pydantic model for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = Field(..., description="User role: 'Team Lead' or 'Process Manager'")

class UserResponse(UserBase):
    """Pydantic model for user data returned in API responses."""
    id: int
    role: UserRole

    class Config:
        from_attributes = True # Enable ORM mode for SQLAlchemy models

class LoginRequest(BaseModel):
    """Pydantic model for user login request."""
    username: str
    password: str

class HealthCheckResponse(BaseModel):
    """Pydantic model for health check response."""
    status: str = "ok"
    message: str = "Service is healthy"
    database_status: Optional[str] = None
    version: str = "1.0.0"