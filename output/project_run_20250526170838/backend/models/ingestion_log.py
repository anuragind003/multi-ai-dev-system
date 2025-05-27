from datetime import datetime
import uuid
from backend.extensions import db


class IngestionLog(db.Model):
    """
    Represents a log entry for data ingestion processes,
    such as file uploads via the Admin Portal.
    """
    __tablename__ = 'ingestion_logs'

    log_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.String(255), nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50))  # e.g., 'SUCCESS', 'FAILED', 'PROCESSING'
    error_description = db.Column(db.Text, nullable=True)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return (f"<IngestionLog(log_id='{self.log_id}', file_name='{self.file_name}', "
                f"status='{self.status}', upload_timestamp='{self.upload_timestamp}')>")

    def to_dict(self):
        """
        Converts the IngestionLog object to a dictionary for JSON serialization.
        """
        return {
            'log_id': self.log_id,
            'file_name': self.file_name,
            'upload_timestamp': self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            'status': self.status,
            'error_description': self.error_description,
            'success_count': self.success_count,
            'error_count': self.error_count
        }

    def save(self):
        """
        Adds the current IngestionLog instance to the database session and commits.
        """
        db.session.add(self)
        db.session.commit()

    def update(self, **kwargs):
        """
        Updates attributes of the IngestionLog instance and commits changes.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()

    @classmethod
    def get_by_id(cls, log_id):
        """
        Retrieves an IngestionLog instance by its log_id.
        """
        return cls.query.get(log_id)

    @classmethod
    def get_all(cls):
        """
        Retrieves all IngestionLog instances, ordered by upload_timestamp descending.
        """
        return cls.query.order_by(cls.upload_timestamp.desc()).all()