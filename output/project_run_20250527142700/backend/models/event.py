import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend.extensions import db

class Event(db.Model):
    """
    Represents an event captured from external systems like Moengage or LOS.
    Events track customer interactions and journey stages.
    """
    __tablename__ = 'events'

    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=True)
    offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=True)
    event_type = db.Column(db.String(100), nullable=False)  # e.g., SMS_SENT, EKYC_ACHIEVED, JOURNEY_LOGIN
    event_timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source_system = db.Column(db.String(50), nullable=False) # e.g., Moengage, LOS
    event_details = db.Column(JSONB, nullable=True) # Raw event payload as JSONB

    # Relationships to other models (using string names to avoid circular imports)
    customer = db.relationship('Customer', backref=db.backref('events', lazy=True))
    offer = db.relationship('Offer', backref=db.backref('events', lazy=True))

    def __init__(self, customer_id: uuid.UUID | str | None, offer_id: uuid.UUID | str | None,
                 event_type: str, source_system: str, event_details: dict | None = None,
                 event_timestamp: datetime | str | None = None):
        """
        Initializes a new Event instance.

        Args:
            customer_id: The UUID of the customer associated with the event. Can be a UUID object or string.
            offer_id: The UUID of the offer associated with the event. Can be a UUID object or string.
            event_type: The type of event (e.g., 'SMS_SENT', 'EKYC_ACHIEVED').
            source_system: The system from which the event originated (e.g., 'Moengage', 'LOS').
            event_details: A dictionary containing additional details about the event.
            event_timestamp: The timestamp of the event. If None, defaults to current UTC time.
                             Can be a datetime object or an ISO-formatted string.
        """
        self.customer_id = uuid.UUID(str(customer_id)) if customer_id else None
        self.offer_id = uuid.UUID(str(offer_id)) if offer_id else None
        self.event_type = event_type
        self.source_system = source_system
        self.event_details = event_details

        if event_timestamp:
            if isinstance(event_timestamp, str):
                try:
                    # Attempt to parse string to datetime, assuming ISO 8601 format
                    dt_obj = datetime.fromisoformat(event_timestamp)
                    # If no timezone info, assume UTC as per database column default
                    if dt_obj.tzinfo is None:
                        self.event_timestamp = dt_obj.replace(tzinfo=timezone.utc)
                    else:
                        self.event_timestamp = dt_obj
                except ValueError:
                    # Fallback to current UTC time if parsing fails
                    self.event_timestamp = datetime.now(timezone.utc)
            elif isinstance(event_timestamp, datetime):
                # If datetime object, ensure it's timezone aware
                if event_timestamp.tzinfo is None:
                    self.event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
                else:
                    self.event_timestamp = event_timestamp
            else:
                # Fallback for unexpected types
                self.event_timestamp = datetime.now(timezone.utc)
        else:
            self.event_timestamp = datetime.now(timezone.utc)

    def save(self):
        """Adds the current event instance to the database session and commits."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Deletes the current event instance from the database session and commits."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, event_id: uuid.UUID | str):
        """
        Retrieves an event by its primary key (event_id).

        Args:
            event_id: The UUID or string representation of the event ID.
        Returns:
            Event: The Event object if found, otherwise None.
        """
        return cls.query.get(uuid.UUID(str(event_id)))

    @classmethod
    def get_by_customer_id(cls, customer_id: uuid.UUID | str, limit: int | None = None):
        """
        Retrieves events associated with a specific customer_id, ordered by timestamp.

        Args:
            customer_id: The UUID or string representation of the customer ID.
            limit: Optional. The maximum number of events to return.
        Returns:
            list[Event]: A list of Event objects.
        """
        query = cls.query.filter_by(customer_id=uuid.UUID(str(customer_id))).order_by(cls.event_timestamp.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_by_offer_id(cls, offer_id: uuid.UUID | str, limit: int | None = None):
        """
        Retrieves events associated with a specific offer_id, ordered by timestamp.

        Args:
            offer_id: The UUID or string representation of the offer ID.
            limit: Optional. The maximum number of events to return.
        Returns:
            list[Event]: A list of Event objects.
        """
        query = cls.query.filter_by(offer_id=uuid.UUID(str(offer_id))).order_by(cls.event_timestamp.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    def to_dict(self) -> dict:
        """
        Converts the event object to a dictionary for JSON serialization.
        """
        return {
            'event_id': str(self.event_id),
            'customer_id': str(self.customer_id) if self.customer_id else None,
            'offer_id': str(self.offer_id) if self.offer_id else None,
            'event_type': self.event_type,
            'event_timestamp': self.event_timestamp.isoformat() if self.event_timestamp else None,
            'source_system': self.source_system,
            'event_details': self.event_details
        }

    def __repr__(self):
        return (f"<Event(event_id='{self.event_id}', event_type='{self.event_type}', "
                f"source_system='{self.source_system}', customer_id='{self.customer_id}')>")