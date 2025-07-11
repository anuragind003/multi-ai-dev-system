python
### FILE: database.py
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os

# Database configuration (using SQLite for simplicity)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db")  # Use environment variable or default
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Task model (SQLAlchemy)
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    completed = Column(Boolean, default=False)

# Create tables (if they don't exist)
Base.metadata.create_all(bind=engine)

# Dependency to get the database session
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()