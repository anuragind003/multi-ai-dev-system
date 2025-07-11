from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from enum import Enum as PyEnum
from sqlalchemy import Enum as SQLEnum

class UserRole(PyEnum):
    """Enum for user roles."""
    TEAM_LEAD = "Team Lead"
    PROCESS_MANAGER = "Process Manager"

class Role(Base):
    """SQLAlchemy model for user roles."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(SQLEnum(UserRole), unique=True, index=True, nullable=False)

    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role(name='{self.name.value}')>"

class User(Base):
    """SQLAlchemy model for users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    role = relationship("Role", back_populates="users")

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role.name.value if self.role else 'N/A'}')>"