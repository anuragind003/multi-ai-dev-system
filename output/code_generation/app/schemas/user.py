from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=64, example="StrongP@ssw0rd")

class UserResponse(UserBase):
    id: int = Field(..., example=1)
    is_active: bool = Field(True, example=True)
    created_at: datetime = Field(..., example="2023-10-27T10:00:00Z")

    model_config = {
        "from_attributes": True # Enable ORM mode for Pydantic
    }

class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., example="StrongP@ssw0rd")

class Token(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field("bearer", example="bearer")

class TokenData(BaseModel):
    email: Optional[str] = None