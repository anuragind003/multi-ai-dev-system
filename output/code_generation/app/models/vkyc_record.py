from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.sql import expression
from database import Base
from datetime import datetime

class VKYCRecord(Base):
    """
    SQLAlchemy ORM model for VKYC (Video Know Your Customer) records.
    Represents a single VKYC recording's metadata.
    """
    __tablename__ = "vkyc_records"

    id = Column(Integer, primary_key=True, index=True)
    lan_id = Column(String, unique=True, index=True, nullable=False, comment="Unique identifier for the VKYC case")
    customer_name = Column(String, nullable=False)
    recording_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    file_path = Column(String, nullable=False, comment="Path to the recording file on NFS")
    status = Column(String, default="completed", comment="Status of the VKYC record (e.g., completed, pending, failed)")
    is_active = Column(Boolean, default=True, server_default=expression.true(), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<VKYCRecord(id={self.id}, lan_id='{self.lan_id}', customer_name='{self.customer_name}')>"