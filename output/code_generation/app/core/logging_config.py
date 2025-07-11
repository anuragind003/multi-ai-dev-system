### FILE: app/models/audit_log.py
import datetime
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class AuditLog(Base):
    """
    SQLAlchemy model for audit logs.
    Records actions performed by users, especially bulk recording downloads.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(sa.String, index=True, nullable=False, comment="ID of the user performing the action")
    action: Mapped[str] = mapped_column(sa.String, nullable=False, comment="Type of action (e.g., 'BULK_DOWNLOAD', 'LOGIN')")
    resource_type: Mapped[str] = mapped_column(sa.String, nullable=False, comment="Type of resource affected (e.g., 'RECORDING', 'USER')")
    resource_id: Mapped[str] = mapped_column(sa.String, nullable=True, comment="Identifier of the resource (e.g., LAN ID for recording)")
    details: Mapped[dict] = mapped_column(JSONB, nullable=True, comment="JSON object for additional details (e.g., list of LAN IDs for bulk download)")
    timestamp: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
        comment="Timestamp of the action"
    )
    ip_address: Mapped[str] = mapped_column(sa.String, nullable=True, comment="IP address of the client")
    user_agent: Mapped[str] = mapped_column(sa.String, nullable=True, comment="User agent string of the client")

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, user_id='{self.user_id}', action='{self.action}', "
            f"resource_type='{self.resource_type}', resource_id='{self.resource_id}', "
            f"timestamp='{self.timestamp}')>"
        )