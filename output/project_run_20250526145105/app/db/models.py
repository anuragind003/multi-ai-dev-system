import uuid

from sqlalchemy import Column, String, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Define the base for declarative models
Base = declarative_base()

class Customer(Base):
    """
    Represents a customer in the Customer Data Platform.
    Stores unique identifiers, attributes, segments, and DND status.
    """
    __tablename__ = 'customers'

    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True, index=True)
    pan_number = Column(String(10), unique=True, index=True)
    aadhaar_ref_number = Column(String(12), unique=True, index=True)
    ucid_number = Column(String(50), unique=True, index=True)
    previous_loan_app_number = Column(String(50), unique=True, index=True)
    customer_attributes = Column(JSONB) # Stores various attributes as JSON
    customer_segments = Column(ARRAY(String)) # Array of segments like C1, C2
    propensity_flag = Column(String(50))
    dnd_status = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    offers = relationship("Offer", back_populates="customer")
    offer_history_entries = relationship("OfferHistory", back_populates="customer")
    campaign_events = relationship("CampaignEvent", back_populates="customer")

    def __repr__(self):
        return f"<Customer(id='{self.customer_id}', mobile='{self.mobile_number}')>"

class Offer(Base):
    """
    Represents a loan offer for a customer.
    Includes offer details, status, type, and journey information.
    """
    __tablename__ = 'offers'

    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    offer_type = Column(String(50)) # e.g., 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = Column(String(50)) # e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'
    product_type = Column(String(50)) # e.g., 'Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan'
    offer_details = Column(JSONB) # Flexible storage for offer specific data
    offer_start_date = Column(Date)
    offer_end_date = Column(Date)
    is_journey_started = Column(Boolean, default=False)
    loan_application_id = Column(String(50), unique=True, index=True) # Populated if journey started
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="offers")
    offer_history_entries = relationship("OfferHistory", back_populates="offer")
    campaign_events = relationship("CampaignEvent", back_populates="offer")

    def __repr__(self):
        return (f"<Offer(id='{self.offer_id}', customer_id='{self.customer_id}', "
                f"product='{self.product_type}', status='{self.offer_status}')>")

class OfferHistory(Base):
    """
    Tracks changes to offer statuses over time for auditing and reference.
    Maintains a snapshot of offer details at the time of change.
    """
    __tablename__ = 'offer_history'

    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    change_timestamp = Column(DateTime(timezone=True), default=func.now())
    old_offer_status = Column(String(50))
    new_offer_status = Column(String(50))
    change_reason = Column(Text)
    snapshot_offer_details = Column(JSONB) # Snapshot of offer details at the time of change

    # Relationships
    offer = relationship("Offer", back_populates="offer_history_entries")
    customer = relationship("Customer", back_populates="offer_history_entries")

    def __repr__(self):
        return (f"<OfferHistory(id='{self.history_id}', offer_id='{self.offer_id}', "
                f"old_status='{self.old_offer_status}', new_status='{self.new_offer_status}')>")

class CampaignEvent(Base):
    """
    Records various campaign and application journey events from sources like Moengage and LOS.
    """
    __tablename__ = 'campaign_events'

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'), nullable=True) # Can be null if not tied to a specific offer
    event_source = Column(String(50)) # e.g., 'Moengage', 'LOS'
    event_type = Column(String(100)) # e.g., 'SMS_SENT', 'CLICK', 'CONVERSION', 'LOGIN'
    event_details = Column(JSONB) # Raw event data
    event_timestamp = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="campaign_events")
    offer = relationship("Offer", back_populates="campaign_events")

    def __repr__(self):
        return (f"<CampaignEvent(id='{self.event_id}', customer_id='{self.customer_id}', "
                f"source='{self.event_source}', type='{self.event_type}')>")