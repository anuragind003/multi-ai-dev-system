from app.extensions import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

class CustomerEvent(db.Model):
    """
    SQLAlchemy model for the 'customer_events' table.
    Stores event data from Moengage and LOS, tracking customer journey and campaign effectiveness.
    """
    __tablename__ = 'customer_events'

    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False) # e.g., 'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICK', 'CONVERSION', 'APP_STAGE_LOGIN'
    event_source = db.Column(db.String(20), nullable=False) # e.g., 'Moengage', 'LOS'
    event_timestamp = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now)
    event_details = db.Column(JSONB) # Stores specific event data (e.g., application stage details)

    # Define relationship with Customer model
    customer = db.relationship('Customer', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f"<CustomerEvent {self.event_id} - Customer: {self.customer_id} - Type: {self.event_type}>"

    def to_dict(self):
        """
        Converts the CustomerEvent object to a dictionary.
        """
        return {
            'event_id': str(self.event_id),
            'customer_id': str(self.customer_id),
            'event_type': self.event_type,
            'event_source': self.event_source,
            'event_timestamp': self.event_timestamp.isoformat() if self.event_timestamp else None,
            'event_details': self.event_details
        }