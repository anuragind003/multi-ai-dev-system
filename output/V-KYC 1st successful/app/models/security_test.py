import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

class UserRole(enum.Enum):
    """Enum for user roles."""
    ADMIN = "admin"
    TESTER = "tester"
    VIEWER = "viewer"

class TestStatus(enum.Enum):
    """Enum for security test statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class VulnerabilitySeverity(enum.Enum):
    """Enum for vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class FindingStatus(enum.Enum):
    """Enum for finding statuses."""
    OPEN = "open"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"

class User(Base):
    """SQLAlchemy model for users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    security_tests = relationship("SecurityTest", back_populates="assigned_to_user")
    vulnerabilities = relationship("Vulnerability", back_populates="reported_by_user")
    findings = relationship("Finding", back_populates="reported_by_user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"

class SecurityTest(Base):
    """SQLAlchemy model for security tests (e.g., penetration tests, vulnerability scans)."""
    __tablename__ = "security_tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    test_type = Column(String, nullable=False) # e.g., "Penetration Test", "Vulnerability Scan"
    target_scope = Column(Text, nullable=False) # e.g., IP ranges, domain names, application URLs
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(TestStatus), default=TestStatus.PENDING, nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    assigned_to_user = relationship("User", back_populates="security_tests")
    vulnerabilities = relationship("Vulnerability", back_populates="security_test", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SecurityTest(id={self.id}, name='{self.name}', status='{self.status.value}')>"

class Vulnerability(Base):
    """SQLAlchemy model for identified vulnerabilities."""
    __tablename__ = "vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    security_test_id = Column(Integer, ForeignKey("security_tests.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Enum(VulnerabilitySeverity), nullable=False)
    cvss_score = Column(String, nullable=True) # Common Vulnerability Scoring System
    cve_id = Column(String, nullable=True) # Common Vulnerabilities and Exposures ID
    remediation_steps = Column(Text, nullable=True)
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    security_test = relationship("SecurityTest", back_populates="vulnerabilities")
    reported_by_user = relationship("User", back_populates="vulnerabilities")
    findings = relationship("Finding", back_populates="vulnerability", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Vulnerability(id={self.id}, name='{self.name}', severity='{self.severity.value}')>"

class Finding(Base):
    """SQLAlchemy model for specific findings related to a vulnerability."""
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    vulnerability_id = Column(Integer, ForeignKey("vulnerabilities.id"), nullable=False)
    title = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    status = Column(Enum(FindingStatus), default=FindingStatus.OPEN, nullable=False)
    affected_asset = Column(String, nullable=True) # e.g., IP address, hostname, URL
    proof_of_concept = Column(Text, nullable=True) # e.g., steps to reproduce, screenshot link
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vulnerability = relationship("Vulnerability", back_populates="findings")
    reported_by_user = relationship("User", back_populates="findings")

    def __repr__(self):
        return f"<Finding(id={self.id}, title='{self.title}', status='{self.status.value}')>"