import uuid
from datetime import datetime
from backend.src.extensions import db

class IngestionLog(db.Model):
    """
    Represents a log entry for data ingestion processes, such as file uploads.
    Corresponds to the 'ingestion_logs' table in the database.
    """
    __tablename__ = 'ingestion_logs'

    log_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.Text, nullable=False)
    upload_timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    status = db.Column(db.Text)  # e.g., 'SUCCESS', 'FAILED', 'PROCESSING'
    error_description = db.Column(db.Text)

    def __init__(self, file_name: str, status: str, error_description: str = None):
        """
        Initializes a new IngestionLog instance.

        Args:
            file_name (str): The name of the file that was ingested.
            status (str): The current status of the ingestion ('SUCCESS', 'FAILED', etc.).
            error_description (str, optional): A description of any error encountered. Defaults to None.
        """
        self.file_name = file_name
        self.status = status
        self.error_description = error_description

    def __repr__(self):
        return (f"<IngestionLog(log_id='{self.log_id}', file_name='{self.file_name}', "
                f"status='{self.status}', upload_timestamp='{self.upload_timestamp}')>")

    def save(self):
        """
        Adds the current log instance to the database session and commits it.
        """
        db.session.add(self)
        db.session.commit()

    @classmethod
    def create(cls, file_name: str, status: str, error_description: str = None):
        """
        Creates a new ingestion log entry and saves it to the database.

        Args:
            file_name (str): The name of the file that was ingested.
            status (str): The initial status of the ingestion.
            error_description (str, optional): A description of any error encountered. Defaults to None.

        Returns:
            IngestionLog: The newly created IngestionLog object.
        """
        new_log = cls(file_name=file_name, status=status, error_description=error_description)
        new_log.save()
        return new_log

    def update_status(self, new_status: str, error_desc: str = None):
        """
        Updates the status and optionally the error description of an existing log entry.

        Args:
            new_status (str): The new status for the ingestion log.
            error_desc (str, optional): An updated error description. Defaults to None.
        """
        self.status = new_status
        self.error_description = error_desc
        db.session.commit()

    @classmethod
    def get_by_id(cls, log_id: str):
        """
        Retrieves an IngestionLog entry by its primary key (log_id).

        Args:
            log_id (str): The UUID of the log entry.

        Returns:
            IngestionLog: The found IngestionLog object, or None if not found.
        """
        return cls.query.get(log_id)

    @classmethod
    def get_all(cls):
        """
        Retrieves all IngestionLog entries.

        Returns:
            list[IngestionLog]: A list of all IngestionLog objects.
        """
        return cls.query.order_by(cls.upload_timestamp.desc()).all()

    @classmethod
    def get_recent_logs(cls, limit: int = 10):
        """
        Retrieves a limited number of the most recent ingestion log entries.

        Args:
            limit (int, optional): The maximum number of logs to retrieve. Defaults to 10.

        Returns:
            list[IngestionLog]: A list of recent IngestionLog objects.
        """
        return cls.query.order_by(cls.upload_timestamp.desc()).limit(limit).all()

    @classmethod
    def get_failed_logs(cls):
        """
        Retrieves all ingestion log entries with a 'FAILED' status.

        Returns:
            list[IngestionLog]: A list of failed IngestionLog objects.
        """
        return cls.query.filter_by(status='FAILED').order_by(cls.upload_timestamp.desc()).all()