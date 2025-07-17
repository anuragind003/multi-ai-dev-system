import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from models.models import UserRole, TestCaseStatus, TestRunStatus

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="Unique email address")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name of the user")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="User password")
    role: Optional[UserRole] = Field(UserRole.QA_ENGINEER, description="User role")

    @validator('password')
    def password_strength(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for char in v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True # For ORM mode

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

# --- Test Case Schemas ---
class TestCaseBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255, description="Title of the test case")
    description: Optional[str] = Field(None, description="Detailed description of the test case")
    steps: str = Field(..., min_length=10, description="Steps to reproduce the test case")
    expected_result: str = Field(..., min_length=5, description="Expected outcome of the test case")
    priority: int = Field(3, ge=1, le=3, description="Priority of the test case (1=High, 2=Medium, 3=Low)")

class TestCaseCreate(TestCaseBase):
    status: Optional[TestCaseStatus] = Field(TestCaseStatus.DRAFT, description="Status of the test case")

class TestCaseUpdate(TestCaseBase):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    steps: Optional[str] = Field(None, min_length=10)
    expected_result: Optional[str] = Field(None, min_length=5)
    status: Optional[TestCaseStatus] = Field(None, description="Status of the test case")

class TestCaseResponse(TestCaseBase):
    id: int
    status: TestCaseStatus
    creator_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Test Run Schemas ---
class TestRunBase(BaseModel):
    test_case_id: int = Field(..., description="ID of the associated test case")
    notes: Optional[str] = Field(None, description="Notes about the test run")
    actual_result: Optional[str] = Field(None, description="Actual result observed during the test run")

class TestRunCreate(TestRunBase):
    pass # No additional fields for creation beyond base

class TestRunUpdate(TestRunBase):
    status: Optional[TestRunStatus] = Field(None, description="Status of the test run")
    start_time: Optional[datetime.datetime] = Field(None, description="Start time of the test run")
    end_time: Optional[datetime.datetime] = Field(None, description="End time of the test run")

class TestRunResponse(TestRunBase):
    id: int
    executor_id: int
    status: TestRunStatus
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime]

    class Config:
        from_attributes = True

# --- Health Check Schema ---
class HealthCheckResponse(BaseModel):
    status: str
    message: str