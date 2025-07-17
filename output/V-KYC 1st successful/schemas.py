from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, TestStatus, VulnerabilitySeverity

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: Optional[UserRole] = UserRole.TESTER

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

class UserUpdate(UserBase):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    @validator('password', pre=True, always=True)
    def validate_password_on_update(cls, v):
        if v is not None:
            return UserCreate.password_strength(v)
        return v

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Authentication Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class LoginRequest(BaseModel):
    username: str
    password: str

# --- Test Project Schemas ---
class TestProjectBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class TestProjectCreate(TestProjectBase):
    status: Optional[TestStatus] = TestStatus.PENDING
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v and values['start_date'] and v < values['start_date']:
            raise ValueError('End date cannot be before start date')
        return v

class TestProjectUpdate(TestProjectCreate):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class TestProjectResponse(TestProjectBase):
    id: int
    owner_id: int
    status: TestStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner: UserResponse # Nested user response

    class Config:
        from_attributes = True

# --- Vulnerability Scan Schemas ---
class VulnerabilityScanBase(BaseModel):
    scan_tool: str = Field(..., max_length=100)
    scan_type: Optional[str] = Field(None, max_length=100)
    status: Optional[TestStatus] = TestStatus.PENDING
    report_path: Optional[str] = Field(None, max_length=255)
    findings_summary: Optional[str] = Field(None, max_length=1000)

class VulnerabilityScanCreate(VulnerabilityScanBase):
    pass

class VulnerabilityScanUpdate(VulnerabilityScanBase):
    scan_tool: Optional[str] = Field(None, max_length=100)

class VulnerabilityScanResponse(VulnerabilityScanBase):
    id: int
    project_id: int
    scan_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Vulnerability Schemas ---
class VulnerabilityBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    severity: VulnerabilitySeverity
    cvss_score: Optional[str] = Field(None, max_length=50)
    remediation: Optional[str] = Field(None, max_length=1000)
    status: str = Field("Open", max_length=50)
    cve_id: Optional[str] = Field(None, max_length=50)

class VulnerabilityCreate(VulnerabilityBase):
    pass

class VulnerabilityUpdate(VulnerabilityBase):
    name: Optional[str] = Field(None, max_length=255)
    severity: Optional[VulnerabilitySeverity] = None
    status: Optional[str] = Field(None, max_length=50)

class VulnerabilityResponse(VulnerabilityBase):
    id: int
    scan_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Penetration Test Schemas ---
class PenetrationTestBase(BaseModel):
    test_type: str = Field(..., max_length=100)
    scope: Optional[str] = Field(None, max_length=500)
    status: Optional[TestStatus] = TestStatus.PENDING
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    report_path: Optional[str] = Field(None, max_length=255)
    findings_summary: Optional[str] = Field(None, max_length=1000)

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v and values['start_date'] and v < values['start_date']:
            raise ValueError('End date cannot be before start date')
        return v

class PenetrationTestCreate(PenetrationTestBase):
    tester_id: int # ID of the user who performed the test

class PenetrationTestUpdate(PenetrationTestBase):
    test_type: Optional[str] = Field(None, max_length=100)
    tester_id: Optional[int] = None

class PenetrationTestResponse(PenetrationTestBase):
    id: int
    project_id: int
    tester_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tester: UserResponse # Nested tester user response

    class Config:
        from_attributes = True

# --- Penetration Test Finding Schemas ---
class PenetrationTestFindingBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    severity: VulnerabilitySeverity
    impact: Optional[str] = Field(None, max_length=1000)
    remediation: Optional[str] = Field(None, max_length=1000)
    status: str = Field("Open", max_length=50)

class PenetrationTestFindingCreate(PenetrationTestFindingBase):
    pass

class PenetrationTestFindingUpdate(PenetrationTestFindingBase):
    name: Optional[str] = Field(None, max_length=255)
    severity: Optional[VulnerabilitySeverity] = None
    status: Optional[str] = Field(None, max_length=50)

class PenetrationTestFindingResponse(PenetrationTestFindingBase):
    id: int
    pen_test_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Health Check Schema ---
class HealthCheckResponse(BaseModel):
    status: str
    database_status: str
    message: str
    timestamp: datetime