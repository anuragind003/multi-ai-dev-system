import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB
from backend import db # Assuming db is initialized in backend/__init__.py

class Customer(db.Model):
    __tablename__ = 'customers'

    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.String(20), unique=True)
    pan_number = db.Column(db.String(10), unique=True)
    aadhaar_number = db.Column(db.String(12), unique=True)
    ucid_number = db.Column(db.String(50), unique=True)
    customer_360_id = db.Column(db.String(50))
    is_dnd = db.Column(db.Boolean, default=False)
    segment = db.Column(db.String(50))
    attributes = db.Column(JSONB)
    created_at = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f"<Customer {self.customer_id} - {self.mobile_number}>"

class Offer(db.Model):
    __tablename__ = 'offers'

    offer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    source_offer_id = db.Column(db.String(100))
    offer_type = db.Column(db.String(50))
    offer_status = db.Column(db.String(50))
    propensity = db.Column(db.String(50))
    loan_application_number = db.Column(db.String(100))
    valid_until = db.Column(db.DateTime(timezone=True))
    source_system = db.Column(db.String(50))
    channel = db.Column(db.String(50))
    is_duplicate = db.Column(db.Boolean, default=False)
    original_offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id')) # Self-referencing
    created_at = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    customer = db.relationship('Customer', backref=db.backref('offers', lazy=True))
    original_offer = db.relationship('Offer', remote_side=[offer_id], backref='duplicate_offers')

    def __repr__(self):
        return f"<Offer {self.offer_id} for Customer {self.customer_id}>"

class OfferHistory(db.Model):
    __tablename__ = 'offer_history'

    history_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=False)
    status_change_date = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp())
    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50))
    change_reason = db.Column(db.Text)

    # Relationships
    offer = db.relationship('Offer', backref=db.backref('history', lazy=True))

    def __repr__(self):
        return f"<OfferHistory {self.history_id} for Offer {self.offer_id}>"

class Event(db.Model):
    __tablename__ = 'events'

    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'))
    offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id'))
    event_type = db.Column(db.String(100), nullable=False)
    event_timestamp = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp())
    source_system = db.Column(db.String(50), nullable=False)
    event_details = db.Column(JSONB)

    # Relationships
    customer = db.relationship('Customer', backref=db.backref('events', lazy=True))
    offer = db.relationship('Offer', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f"<Event {self.event_id} - {self.event_type}>"

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    campaign_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_date = db.Column(db.Date, nullable=False)
    campaign_unique_identifier = db.Column(db.String(100), unique=True, nullable=False)
    attempted_count = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Numeric(5, 2), default=0.0)
    conversion_rate = db.Column(db.Numeric(5, 2), default=0.0)
    created_at = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __repr__(self):
        return f"<Campaign {self.campaign_id} - {self.campaign_name}>"