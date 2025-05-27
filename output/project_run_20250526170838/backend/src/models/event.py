import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from backend.src.extensions import db # Assuming db is initialized here

class Event(db.Model):
    __tablename__ = 'events'

    event_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.Text, nullable=False)
    event_source = db.Column(db.Text, nullable=False)
    event_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    event_details = db.Column(JSONB)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to Customer model (assuming Customer model exists)
    customer = db.relationship('Customer', backref='events', lazy=True)

    def __repr__(self):
        return f"<Event {self.event_id} - Type: {self.event_type} - Source: {self.event_source}>"

    def to_dict(self):
        """Converts the Event object to a dictionary."""
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
    def create(cls, customer_id, event_type, event_source, event_timestamp=None, event_details=None):
        """
        Creates a new event record.

        Args:
            customer_id (str): The ID of the customer associated with the event.
            event_type (str): The type of event (e.g., 'SMS_SENT', 'EKYC_ACHIEVED').
            event_source (str): The source system of the event (e.g., 'Moengage', 'LOS').
            event_timestamp (datetime, optional): The timestamp of the event. Defaults to current UTC time.
            event_details (dict, optional): A dictionary for flexible event-specific data.

        Returns:
            Event: The newly created Event object.
        """
        if event_timestamp is None:
            event_timestamp = datetime.utcnow()

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
    def get_by_customer_id(cls, customer_id):
        """
        Retrieves all events for a given customer ID, ordered by timestamp.

        Args:
            customer_id (str): The ID of the customer.

        Returns:
            list[Event]: A list of Event objects.
        """
        return cls.query.filter_by(customer_id=customer_id).order_by(cls.event_timestamp.asc()).all()

    @classmethod
    def get_by_event_id(cls, event_id):
        """
        Retrieves an event by its ID.

        Args:
            event_id (str): The ID of the event.

        Returns:
            Event or None: The Event object if found, otherwise None.
        """
        return cls.query.get(event_id)

    @classmethod
    def get_events_by_type_and_source(cls, event_type, event_source, limit=None):
        """
        Retrieves events filtered by type and source.

        Args:
            event_type (str): The type of event.
            event_source (str): The source system of the event.
            limit (int, optional): Maximum number of events to return.

        Returns:
            list[Event]: A list of Event objects.
        """
        query = cls.query.filter_by(event_type=event_type, event_source=event_source)
        if limit:
            query = query.limit(limit)
        return query.all()