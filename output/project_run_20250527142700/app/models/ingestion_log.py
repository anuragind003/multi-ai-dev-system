import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# Assuming db is initialized in app/extensions.py
# This import path might need adjustment based on the actual project structure
# where `db = SQLAlchemy(app)` is initialized.
try:
    from app.extensions import db
except ImportError:
    # Fallback for local testing or if db is initialized differently
    # In a real Flask app, ensure `db` is properly initialized and imported.
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy() # This won't work without an app context, but serves as a placeholder


class IngestionLog(db.Model):
    """
    Represents a log entry for data ingestion processes, such as file uploads
    from the Admin Portal.
    """
    __tablename__ = 'data_ingestion_logs'

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), default=func.now())
    status = Column(String(20), nullable=False) # 'SUCCESS', 'FAILED', 'PARTIAL'
    error_details = Column(Text, nullable=True)
    uploaded_by = Column(String(100), nullable=True)

    def __repr__(self):
        return (f"<IngestionLog(log_id='{self.log_id}', "
                f"file_name='{self.file_name}', status='{self.status}')>")

    def to_dict(self):
        """
        Converts the IngestionLog object to a dictionary for serialization.
        """
        return {
            'log_id': str(self.log_id),
            'file_name': self.file_name,
            'upload_timestamp': self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            'status': self.status,
            'error_details': self.error_details,
            'uploaded_by': self.uploaded_by
        }