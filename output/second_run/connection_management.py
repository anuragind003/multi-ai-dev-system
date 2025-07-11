# connection_management.py
# Manages database connections using SQLAlchemy.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from database_configuration import DatabaseConfig

# Create a database configuration instance.
db_config = DatabaseConfig()
DATABASE_URL = db_config.get_db_url()

# Create a SQLAlchemy engine.
engine = create_engine(DATABASE_URL)

# Create a session factory.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for declarative models.
Base = declarative_base()

# Context manager for database sessions.
class SessionManager:
    def __init__(self):
        self.db = None

    def __enter__(self):
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.db.rollback()
            else:
                self.db.commit()
        except Exception as e:
            print(f"Error during session cleanup: {e}")
            self.db.rollback()  # Ensure rollback on any error during commit.
        finally:
            self.db.close()