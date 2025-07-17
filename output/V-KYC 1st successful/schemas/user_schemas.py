from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# --- Request Schemas ---

class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr = Field(..., example="admin@example.com", description="Unique email address for the user.")
    password: str = Field(..., min_length=8, example="StrongP@ssw0rd", description="User's password (min 8 characters).")

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., example="admin@example.com")
    password: str = Field(..., example="StrongP@ssw0rd")

# --- Response Schemas ---

class UserResponse(BaseModel):
    """Schema for returning user data (excluding password hash)."""
    id: int = Field(..., example=1)
    email: EmailStr = Field(..., example="admin@example.com")
    is_active: bool = Field(True, example=True)
    is_superuser: bool = Field(False, example=False)

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field("bearer", example="bearer")

class TokenData(BaseModel):
    """Schema for data contained within a JWT token."""
    email: Optional[str] = None