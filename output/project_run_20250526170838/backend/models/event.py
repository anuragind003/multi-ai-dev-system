import uuid
from datetime import datetime
from backend.app import db  # Assuming db is initialized in backend/app.py

class Event(db.Model):
    """
    Represents an event related to a customer's journey or interaction.
    Events can include SMS interactions, application stages, conversions, etc.
    """
    __tablename__ = 'events'

    event_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.Text, nullable=False)  # e.g., 'SMS_SENT', 'EKYC_ACHIEVED', 'LOAN_LOGIN'
    event_source = db.Column(db.Text, nullable=False)  # e.g., 'Moengage', 'LOS', 'E-aggregator'
    event_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_details = db.Column(db.JSONB)  # Flexible storage for event-specific data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationship with Customer model (assuming Customer model exists)
    customer = db.relationship('Customer', backref='events', lazy=True)

    def __init__(self, customer_id, event_type, event_source,
                 event_timestamp=None, event_details=None):
        self.customer_id = customer_id
        self.event_type = event_type
        self.event_source = event_source
        self.event_timestamp = event_timestamp if event_timestamp else datetime.utcnow()
        self.event_details = event_details

    def __repr__(self):
        return (f"<Event(event_id='{self.event_id}', "
                f"customer_id='{self.customer_id}', "
                f"event_type='{self.event_type}', "
                f"event_source='{self.event_source}')>")

    def to_dict(self):
        """
        Converts the Event object to a dictionary for JSON serialization.
        """
        return {
            'event_id': self.event_id,
            'customer_id': self.customer_id,
            'event_type': self.event_type,
            'event_source': self.event_source,
            'event_timestamp': self.event_timestamp.isoformat() if self.event_timestamp else None,
            'event_details': self.event_details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create_event(cls, customer_id, event_type, event_source,
                     event_timestamp=None, event_details=None):
        """
        Creates a new event record in the database.
        """
        new_event = cls(
            customer_id=customer_id,
            event_type=event_type,
            event_source=event_source,
            event_timestamp=event_timestamp,
            event_details=event_details
        )
        db.session.add(new_event)
        db.session.commit()
        return new_event

    @classmethod
    def get_events_by_customer(cls, customer_id, limit=None):
        """
        Retrieves events for a specific customer, ordered by timestamp.
        """
        query = cls.query.filter_by(customer_id=customer_id).order_by(
            cls.event_timestamp.desc()
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_event_by_id(cls, event_id):
        """
        Retrieves a single event by its ID.
        """
        return cls.query.get(event_id)