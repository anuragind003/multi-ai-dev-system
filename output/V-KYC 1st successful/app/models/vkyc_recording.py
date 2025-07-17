from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from app.core.database import Base
import logging

logger = logging.getLogger(__name__)

class VKYCRecording(Base):
    """
    SQLAlchemy model for the 'vkyc_recordings' table.
    Stores metadata about VKYC recordings.
    """
    __tablename__ = "vkyc_recordings"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, unique=True, index=True, nullable=False) # Unique identifier for the recording
    recording_date = Column(DateTime, nullable=False)
    file_path = Column(String, nullable=False) # Path to the recording file on NFS
    status = Column(String, default="PENDING", nullable=False) # e.g., PENDING, PROCESSED, FAILED
    uploaded_by = Column(String, nullable=False) # User who uploaded/ingested the metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return (
            f"<VKYCRecording(id={self.id}, lan_id='{self.lan_id}', "
            f"recording_date='{self.recording_date.isoformat()}', status='{self.status}')>"
        )

# Example of how to create tables (for development/testing)
# In a production environment, use Alembic for migrations.
def create_tables():
    """Creates all tables defined in Base metadata."""
    try:
        Base.metadata.create_all(bind=Base.metadata.bind)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise