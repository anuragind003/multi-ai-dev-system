from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TESTER = "tester"
    VIEWER = "viewer"

class TestStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class VulnerabilitySeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.TESTER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    test_projects = relationship("TestProject", back_populates="owner")

class TestProject(Base):
    __tablename__ = "test_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(TestStatus), default=TestStatus.PENDING, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="test_projects")
    vulnerability_scans = relationship("VulnerabilityScan", back_populates="project")
    penetration_tests = relationship("PenetrationTest", back_populates="project")

class VulnerabilityScan(Base):
    __tablename__ = "vulnerability_scans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("test_projects.id"), nullable=False)
    scan_tool = Column(String, nullable=False) # e.g., Nessus, OpenVAS, Qualys
    scan_type = Column(String, nullable=True) # e.g., Web Application, Network, Cloud
    status = Column(Enum(TestStatus), default=TestStatus.PENDING, nullable=False)
    scan_date = Column(DateTime(timezone=True), server_default=func.now())
    report_path = Column(String, nullable=True) # Path to the scan report file
    findings_summary = Column(Text, nullable=True) # Summary of findings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("TestProject", back_populates="vulnerability_scans")
    vulnerabilities = relationship("Vulnerability", back_populates="scan")

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("vulnerability_scans.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Enum(VulnerabilitySeverity), nullable=False)
    cvss_score = Column(String, nullable=True) # e.g., "7.5 (High)"
    remediation = Column(Text, nullable=True)
    status = Column(String, default="Open", nullable=False) # e.g., Open, Fixed, False Positive
    cve_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    scan = relationship("VulnerabilityScan", back_populates="vulnerabilities")

class PenetrationTest(Base):
    __tablename__ = "penetration_tests"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("test_projects.id"), nullable=False)
    tester_id = Column(Integer, ForeignKey("users.id"), nullable=False) # The user who performed the test
    test_type = Column(String, nullable=False) # e.g., Black Box, White Box, Grey Box
    scope = Column(Text, nullable=True)
    status = Column(Enum(TestStatus), default=TestStatus.PENDING, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    report_path = Column(String, nullable=True) # Path to the pen test report file
    findings_summary = Column(Text, nullable=True) # Summary of findings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("TestProject", back_populates="penetration_tests")
    tester = relationship("User", foreign_keys=[tester_id]) # Relationship to the User who is the tester
    findings = relationship("PenetrationTestFinding", back_populates="pen_test")

class PenetrationTestFinding(Base):
    __tablename__ = "penetration_test_findings"

    id = Column(Integer, primary_key=True, index=True)
    pen_test_id = Column(Integer, ForeignKey("penetration_tests.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Enum(VulnerabilitySeverity), nullable=False)
    impact = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)
    status = Column(String, default="Open", nullable=False) # e.g., Open, Fixed, Accepted Risk
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pen_test = relationship("PenetrationTest", back_populates="findings")