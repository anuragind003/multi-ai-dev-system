from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr, validator

from app.models.security_test import UserRole, TestStatus, VulnerabilitySeverity, FindingStatus

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")
    role: UserRole = Field(UserRole.VIEWER, description="User's role (admin, tester, viewer)")
    is_active: bool = Field(True, description="Is the user account active?")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="User's password")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, description="New password if updating")

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    roles: List[UserRole] = []

# --- Security Test Schemas ---
class SecurityTestBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="Name of the security test")
    description: Optional[str] = Field(None, max_length=1000, description="Detailed description of the test")
    test_type: str = Field(..., description="Type of test (e.g., 'Penetration Test', 'Vulnerability Scan')")
    target_scope: str = Field(..., max_length=1000, description="Scope of the test (e.g., IP ranges, URLs)")
    start_date: Optional[datetime] = Field(None, description="Planned or actual start date of the test")
    end_date: Optional[datetime] = Field(None, description="Planned or actual end date of the test")
    status: TestStatus = Field(TestStatus.PENDING, description="Current status of the test")
    assigned_to: Optional[int] = Field(None, description="ID of the user assigned to this test")

    @validator('end_date', pre=True, always=True)
    def validate_dates(cls, v, values):
        if 'start_date' in values and values['start_date'] and v and v < values['start_date']:
            raise ValueError('End date cannot be before start date')
        return v

class SecurityTestCreate(SecurityTestBase):
    pass

class SecurityTestUpdate(SecurityTestBase):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    test_type: Optional[str] = None
    target_scope: Optional[str] = None
    status: Optional[TestStatus] = None

class SecurityTestResponse(SecurityTestBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    assigned_to_user: Optional[UserResponse] = None # Nested user response

    class Config:
        from_attributes = True

# --- Vulnerability Schemas ---
class VulnerabilityBase(BaseModel):
    security_test_id: int = Field(..., description="ID of the security test this vulnerability belongs to")
    name: str = Field(..., min_length=3, max_length=255, description="Name of the vulnerability (e.g., 'SQL Injection')")
    description: Optional[str] = Field(None, max_length=1000, description="Detailed description of the vulnerability")
    severity: VulnerabilitySeverity = Field(..., description="Severity of the vulnerability")
    cvss_score: Optional[str] = Field(None, max_length=50, description="CVSS score string (e.g., 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H')")
    cve_id: Optional[str] = Field(None, max_length=50, description="CVE ID (e.g., 'CVE-2023-1234')")
    remediation_steps: Optional[str] = Field(None, max_length=2000, description="Steps to remediate the vulnerability")
    reported_by: Optional[int] = Field(None, description="ID of the user who reported this vulnerability")

class VulnerabilityCreate(VulnerabilityBase):
    pass

class VulnerabilityUpdate(VulnerabilityBase):
    security_test_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    severity: Optional[VulnerabilitySeverity] = None

class VulnerabilityResponse(VulnerabilityBase):
    id: int
    reported_at: datetime
    updated_at: Optional[datetime]
    reported_by_user: Optional[UserResponse] = None # Nested user response
    # findings: List['FindingResponse'] = [] # Forward reference for nested findings

    class Config:
        from_attributes = True

# --- Finding Schemas ---
class FindingBase(BaseModel):
    vulnerability_id: int = Field(..., description="ID of the vulnerability this finding belongs to")
    title: str = Field(..., min_length=3, max_length=255, description="Title of the specific finding")
    details: Optional[str] = Field(None, max_length=1000, description="Detailed description of the finding")
    status: FindingStatus = Field(FindingStatus.OPEN, description="Current status of the finding")
    affected_asset: Optional[str] = Field(None, max_length=255, description="Affected asset (e.g., IP, hostname, URL)")
    proof_of_concept: Optional[str] = Field(None, max_length=2000, description="Proof of concept or steps to reproduce")
    reported_by: Optional[int] = Field(None, description="ID of the user who reported this finding")

class FindingCreate(FindingBase):
    pass

class FindingUpdate(FindingBase):
    vulnerability_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    status: Optional[FindingStatus] = None

class FindingResponse(FindingBase):
    id: int
    reported_at: datetime
    updated_at: Optional[datetime]
    reported_by_user: Optional[UserResponse] = None # Nested user response

    class Config:
        from_attributes = True

# Update forward references for nested schemas
VulnerabilityResponse.model_rebuild()
# If you want to nest findings within vulnerability, uncomment and rebuild
# VulnerabilityResponse.update_forward_refs()