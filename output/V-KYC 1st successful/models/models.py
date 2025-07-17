import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from database import Base

class UserRole(str, enum.Enum):
    """Enum for user roles."""
    ADMIN = "admin"
    QA_ENGINEER = "qa_engineer"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class TestCaseStatus(str, enum.Enum):
    """Enum for test case statuses."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class TestRunStatus(str, enum.Enum):
    """Enum for test run statuses."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class User(Base):
    """SQLAlchemy model for users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.QA_ENGINEER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))

    test_cases = relationship("TestCase", back_populates="creator")
    test_runs = relationship("TestRun", back_populates="executor")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

class TestCase(Base):
    """SQLAlchemy model for test cases."""
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    steps = Column(Text, nullable=False) # Markdown or plain text for steps
    expected_result = Column(Text, nullable=False)
    priority = Column(Integer, default=3, nullable=False) # 1: High, 2: Medium, 3: Low
    status = Column(Enum(TestCaseStatus), default=TestCaseStatus.DRAFT, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))

    creator = relationship("User", back_populates="test_cases")
    test_runs = relationship("TestRun", back_populates="test_case")

    def __repr__(self):
        return f"<TestCase(id={self.id}, title='{self.title}', status='{self.status}')>"

class TestRun(Base):
    """SQLAlchemy model for test runs."""
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(TestRunStatus), default=TestRunStatus.PENDING, nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    end_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    actual_result = Column(Text, nullable=True)

    test_case = relationship("TestCase", back_populates="test_runs")
    executor = relationship("User", back_populates="test_runs")

    def __repr__(self):
        return f"<TestRun(id={self.id}, test_case_id={self.test_case_id}, status='{self.status}')>"