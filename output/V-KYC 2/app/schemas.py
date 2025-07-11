from pydantic import BaseModel, Field, EmailStr
from typing import Optional

# --- User Schemas ---

class UserBase(BaseModel):
    """Base schema for user data."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username for the user.")
    email: Optional[EmailStr] = Field(None, description="Optional email address for the user.")

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="Password for the user. Must be at least 8 characters.")

class UserLogin(BaseModel):
    """Schema for user login requests."""
    username: str = Field(..., description="Username for login.")
    password: str = Field(..., description="Password for login.")

class UserResponse(UserBase):
    """Schema for returning user data (excluding sensitive info like password hash)."""
    id: int = Field(..., description="Unique identifier for the user.")
    is_active: bool = Field(True, description="Indicates if the user account is active.")

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2+

# --- Token Schemas ---

class Token(BaseModel):
    """Schema for JWT access token response."""
    access_token: str = Field(..., description="The JWT access token.")
    token_type: str = Field("bearer", description="Type of the token (e.g., 'bearer').")

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    username: Optional[str] = Field(None, description="Username extracted from the token.")

# --- Error Schemas ---

class HTTPError(BaseModel):
    """Standard schema for HTTP error responses."""
    detail: str = Field(..., description="A detailed error message.")

    class Config:
        json_schema_extra = {
            "examples": [
                {"detail": "User not found"},
                {"detail": "Invalid credentials"},
            ]
        }

# --- Health Check Schemas ---

class HealthStatus(BaseModel):
    """Schema for health check responses."""
    status: str = Field(..., description="Overall health status (e.g., 'OK', 'Degraded', 'Error').")
    database: str = Field(..., description="Database connection status.")
    message: Optional[str] = Field(None, description="Additional health information or error message.")