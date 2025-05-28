from backend import db
import uuid
import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import func, text
from sqlalchemy.orm import relationship

class Customer(db.Model):
    __tablename__ = 'customers'

    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.String(20), unique=True, nullable=True)
    pan_number = db.Column(db.String(10), unique=True, nullable=True)
    aadhaar_number = db.Column(db.String(12), unique=True, nullable=True)
    ucid_number = db.Column(db.String(50), unique=True, nullable=True)
    customer_360_id = db.Column(db.String(50), nullable=True)
    is_dnd = db.Column(db.Boolean, default=False, nullable=False)
    segment = db.Column(db.String(50), nullable=True)
    attributes = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)

    offers = relationship('Offer', backref='customer', lazy=True)
    events = relationship('Event', backref='customer', lazy=True)

    def __repr__(self):
        return f"<Customer {self.customer_id} - {self.mobile_number}>"

class Offer(db.Model):
    __tablename__ = 'offers'

    offer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    source_offer_id = db.Column(db.String(100), nullable=True)
    offer_type = db.Column(db.String(50), nullable=True) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.String(50), nullable=False) # 'Active', 'Inactive', 'Expired'
    propensity = db.Column(db.String(50), nullable=True)
    loan_application_number = db.Column(db.String(100), nullable=True)
    valid_until = db.Column(db.DateTime(timezone=True), nullable=True)
    source_system = db.Column(db.String(50), nullable=True) # 'Offermart', 'E-aggregator'
    channel = db.Column(db.String(50), nullable=True) # For attribution
    is_duplicate = db.Column(db.Boolean, default=False, nullable=False)
    original_offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=True) # Points to the offer it duplicated/enriched
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)

    offer_history = relationship('OfferHistory', backref='offer', lazy=True)
    events = relationship('Event', backref='offer', lazy=True)
    
    # Self-referential relationship for original_offer_id
    duplicate_offers = relationship('Offer', backref=db.backref('original_offer', remote_side=[offer_id]), lazy=True)

    def __repr__(self):
        return f"<Offer {self.offer_id} - Customer: {self.customer_id} - Status: {self.offer_status}>"

class OfferHistory(db.Model):
    __tablename__ = 'offer_history'

    history_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=False)
    status_change_date = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    old_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    change_reason = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<OfferHistory {self.history_id} - Offer: {self.offer_id} - New Status: {self.new_status}>"

class Event(db.Model):
    __tablename__ = 'events'

    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=True)
    offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=True)
    event_type = db.Column(db.String(100), nullable=False) # SMS_SENT, EKYC_ACHIEVED, JOURNEY_LOGIN, etc.
    event_timestamp = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    source_system = db.Column(db.String(50), nullable=False) # Moengage, LOS
    event_details = db.Column(JSONB, nullable=True) # Raw event payload

    def __repr__(self):
        return f"<Event {self.event_id} - Type: {self.event_type} - Source: {self.source_system}>"

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    campaign_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_date = db.Column(db.Date, nullable=False)
    campaign_unique_identifier = db.Column(db.String(100), unique=True, nullable=False)
    attempted_count = db.Column(db.Integer, default=0, nullable=False)
    sent_count = db.Column(db.Integer, default=0, nullable=False)
    failed_count = db.Column(db.Integer, default=0, nullable=False)
    success_rate = db.Column(db.Numeric(5,2), default=0.0, nullable=False)
    conversion_rate = db.Column(db.Numeric(5,2), default=0.0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False)

    def __repr__(self):
        return f"<Campaign {self.campaign_id} - {self.campaign_name}>"