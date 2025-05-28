import pytest
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, Numeric, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
import uuid
from datetime import datetime, date, timedelta
import time

# --- Mock Models (In a real project, these would be imported from backend.src.models) ---
# For the purpose of this specific file generation, we define them here to make the test file self-contained.
# In a real project, you would typically have:
# from backend.src.models import Base, Customer, Offer, OfferHistory, Event, Campaign

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True)
    pan_number = Column(String(10), unique=True)
    aadhaar_number = Column(String(12), unique=True)
    ucid_number = Column(String(50), unique=True)
    customer_360_id = Column(String(50))
    is_dnd = Column(Boolean, default=False)
    segment = Column(String(50))
    attributes = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    offers = relationship("Offer", back_populates="customer", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer(id={self.customer_id}, mobile='{self.mobile_number}')>"

class Offer(Base):
    __tablename__ = 'offers'
    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    source_offer_id = Column(String(100))
    offer_type = Column(String(50))
    offer_status = Column(String(50))
    propensity = Column(String(50))
    loan_application_number = Column(String(100))
    valid_until = Column(DateTime(timezone=True))
    source_system = Column(String(50))
    channel = Column(String(50))
    is_duplicate = Column(Boolean, default=False)
    original_offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id')) # Self-referencing FK
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    customer = relationship("Customer", back_populates="offers")
    original_offer = relationship("Offer", remote_side=[offer_id], backref="duplicate_offers")
    history = relationship("OfferHistory", back_populates="offer", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="offer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Offer(id={self.offer_id}, customer_id={self.customer_id}, status='{self.offer_status}')>"

class OfferHistory(Base):
    __tablename__ = 'offer_history'
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'), nullable=False)
    status_change_date = Column(DateTime(timezone=True), default=func.now())
    old_status = Column(String(50))
    new_status = Column(String(50))
    change_reason = Column(Text)

    offer = relationship("Offer", back_populates="history")

    def __repr__(self):
        return f"<OfferHistory(id={self.history_id}, offer_id={self.offer_id}, new_status='{self.new_status}')>"

class Event(Base):
    __tablename__ = 'events'
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'))
    offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'))
    event_type = Column(String(100), nullable=False)
    event_timestamp = Column(DateTime(timezone=True), default=func.now())
    source_system = Column(String(50), nullable=False)
    event_details = Column(JSONB)

    customer = relationship("Customer", back_populates="events")
    offer = relationship("Offer", back_populates="events")

    def __repr__(self):
        return f"<Event(id={self.event_id}, type='{self.event_type}', source='{self.source_system}')>"

class Campaign(Base):
    __tablename__ = 'campaigns'
    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_name = Column(String(255), nullable=False)
    campaign_date = Column(Date, nullable=False)
    campaign_unique_identifier = Column(String(100), unique=True, nullable=False)
    attempted_count = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    success_rate = Column(Numeric(5,2), default=0.0)
    conversion_rate = Column(Numeric(5,2), default=0.0)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Campaign(id={self.campaign_id}, name='{self.campaign_name}')>"

# --- End Mock Models ---

@pytest.fixture(scope='function')
def db_session():
    """
    Provides a SQLAlchemy session for testing.
    Uses an in-memory SQLite database for speed.
    """
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_customer_creation(db_session):
    """Test creating a new Customer record."""
    customer = Customer(
        mobile_number="9876543210",
        pan_number="ABCDE1234F",
        segment="C1",
        attributes={"city": "Mumbai", "age": 30}
    )
    db_session.add(customer)
    db_session.commit()

    retrieved_customer = db_session.query(Customer).filter_by(mobile_number="9876543210").first()
    assert retrieved_customer is not None
    assert retrieved_customer.customer_id is not None
    assert retrieved_customer.mobile_number == "9876543210"
    assert retrieved_customer.pan_number == "ABCDE1234F"
    assert retrieved_customer.is_dnd is False # Test default value
    assert retrieved_customer.segment == "C1"
    assert retrieved_customer.attributes == {"city": "Mumbai", "age": 30}
    assert retrieved_customer.created_at is not None
    assert retrieved_customer.updated_at is not None
    assert isinstance(retrieved_customer.customer_id, uuid.UUID)
    assert retrieved_customer.created_at == retrieved_customer.updated_at # Initially, they should be the same

def test_customer_update_timestamp(db_session):
    """Test that updated_at timestamp is updated on modification."""
    customer = Customer(mobile_number="1234567890", pan_number="TESTPAN")
    db_session.add(customer)
    db_session.commit()

    initial_updated_at = customer.updated_at
    time.sleep(0.01) # Ensure a measurable time difference

    customer.segment = "C2"
    db_session.commit()

    retrieved_customer = db_session.query(Customer).filter_by(mobile_number="1234567890").first()
    assert retrieved_customer.updated_at > initial_updated_at

def test_customer_unique_constraints(db_session):
    """Test unique constraints on Customer fields."""
    customer1 = Customer(mobile_number="1111111111", pan_number="PAN1", aadhaar_number="AADHAAR1", ucid_number="UCID1")
    db_session.add(customer1)
    db_session.commit()

    # Attempt to add customer with duplicate mobile_number
    customer2 = Customer(mobile_number="1111111111", pan_number="PAN2")
    db_session.add(customer2)
    with pytest.raises(Exception): # SQLAlchemy might raise IntegrityError or similar
        db_session.commit()
    db_session.rollback() # Rollback the failed transaction

    # Attempt to add customer with duplicate pan_number
    customer3 = Customer(mobile_number="2222222222", pan_number="PAN1")
    db_session.add(customer3)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()

def test_offer_creation(db_session):
    """Test creating a new Offer record and its relationship to Customer."""
    customer = Customer(mobile_number="9999999999")
    db_session.add(customer)
    db_session.commit()

    offer = Offer(
        customer_id=customer.customer_id,
        source_offer_id="OFFER123",
        offer_type="Fresh",
        offer_status="Active",
        propensity="High",
        valid_until=datetime.now() + timedelta(days=30),
        source_system="Offermart",
        channel="SMS"
    )
    db_session.add(offer)
    db_session.commit()

    retrieved_offer = db_session.query(Offer).filter_by(source_offer_id="OFFER123").first()
    assert retrieved_offer is not None
    assert retrieved_offer.offer_id is not None
    assert retrieved_offer.customer_id == customer.customer_id
    assert retrieved_offer.offer_status == "Active"
    assert retrieved_offer.is_duplicate is False # Test default value
    assert retrieved_offer.created_at is not None
    assert retrieved_offer.updated_at is not None
    assert isinstance(retrieved_offer.offer_id, uuid.UUID)
    assert retrieved_offer.customer is not None
    assert retrieved_offer.customer.mobile_number == "9999999999"
    assert retrieved_offer.created_at == retrieved_offer.updated_at

def test_offer_update_timestamp(db_session):
    """Test that updated_at timestamp is updated on offer modification."""
    customer = Customer(mobile_number="1111111112")
    db_session.add(customer)
    db_session.commit()

    offer = Offer(customer_id=customer.customer_id, offer_status="Active")
    db_session.add(offer)
    db_session.commit()

    initial_updated_at = offer.updated_at
    time.sleep(0.01)

    offer.offer_status = "Inactive"
    db_session.commit()

    retrieved_offer = db_session.query(Offer).filter_by(offer_id=offer.offer_id).first()
    assert retrieved_offer.updated_at > initial_updated_at

def test_offer_history_creation(db_session):
    """Test creating an OfferHistory record and its relationship to Offer."""
    customer = Customer(mobile_number="1112223334")
    db_session.add(customer)
    db_session.commit()

    offer = Offer(customer_id=customer.customer_id, offer_status="Active")
    db_session.add(offer)
    db_session.commit()

    history = OfferHistory(
        offer_id=offer.offer_id,
        old_status="Active",
        new_status="Expired",
        change_reason="LAN validity over"
    )
    db_session.add(history)
    db_session.commit()

    retrieved_history = db_session.query(OfferHistory).filter_by(offer_id=offer.offer_id).first()
    assert retrieved_history is not None
    assert retrieved_history.history_id is not None
    assert retrieved_history.offer_id == offer.offer_id
    assert retrieved_history.new_status == "Expired"
    assert retrieved_history.status_change_date is not None
    assert retrieved_history.offer is not None
    assert retrieved_history.offer.offer_status == "Active" # Status on offer itself is not changed by history entry

def test_event_creation(db_session):
    """Test creating an Event record and its relationships."""
    customer = Customer(mobile_number="1234567890")
    db_session.add(customer)
    db_session.commit()

    offer = Offer(customer_id=customer.customer_id, offer_status="Active")
    db_session.add(offer)
    db_session.commit()

    event = Event(
        customer_id=customer.customer_id,
        offer_id=offer.offer_id,
        event_type="SMS_SENT",
        source_system="Moengage",
        event_details={"message_id": "msg123", "status": "sent"}
    )
    db_session.add(event)
    db_session.commit()

    retrieved_event = db_session.query(Event).filter_by(event_type="SMS_SENT").first()
    assert retrieved_event is not None
    assert retrieved_event.event_id is not None
    assert retrieved_event.customer_id == customer.customer_id
    assert retrieved_event.offer_id == offer.offer_id
    assert retrieved_event.source_system == "Moengage"
    assert retrieved_event.event_details == {"message_id": "msg123", "status": "sent"}
    assert retrieved_event.event_timestamp is not None
    assert retrieved_event.customer is not None
    assert retrieved_event.offer is not None

def test_campaign_creation(db_session):
    """Test creating a new Campaign record."""
    campaign = Campaign(
        campaign_name="Summer Loan Offer",
        campaign_date=date(2023, 7, 15),
        campaign_unique_identifier="SUMMER2023_LOAN",
        attempted_count=1000,
        sent_count=950,
        failed_count=50,
        success_rate=95.00,
        conversion_rate=5.25
    )
    db_session.add(campaign)
    db_session.commit()

    retrieved_campaign = db_session.query(Campaign).filter_by(campaign_unique_identifier="SUMMER2023_LOAN").first()
    assert retrieved_campaign is not None
    assert retrieved_campaign.campaign_id is not None
    assert retrieved_campaign.campaign_name == "Summer Loan Offer"
    assert retrieved_campaign.campaign_date == date(2023, 7, 15)
    assert retrieved_campaign.attempted_count == 1000
    assert retrieved_campaign.success_rate == 95.00
    assert retrieved_campaign.conversion_rate == 5.25
    assert retrieved_campaign.created_at is not None
    assert retrieved_campaign.updated_at is not None
    assert isinstance(retrieved_campaign.campaign_id, uuid.UUID)
    assert retrieved_campaign.created_at == retrieved_campaign.updated_at

def test_campaign_update_timestamp(db_session):
    """Test that updated_at timestamp is updated on campaign modification."""
    campaign = Campaign(
        campaign_name="Winter Campaign",
        campaign_date=date(2023, 12, 1),
        campaign_unique_identifier="WINTER2023_CAMPAIGN"
    )
    db_session.add(campaign)
    db_session.commit()

    initial_updated_at = campaign.updated_at
    time.sleep(0.01)

    campaign.attempted_count = 1500
    db_session.commit()

    retrieved_campaign = db_session.query(Campaign).filter_by(campaign_unique_identifier="WINTER2023_CAMPAIGN").first()
    assert retrieved_campaign.updated_at > initial_updated_at

def test_campaign_unique_identifier_constraint(db_session):
    """Test unique constraint on campaign_unique_identifier."""
    campaign1 = Campaign(
        campaign_name="Campaign A",
        campaign_date=date(2023, 1, 1),
        campaign_unique_identifier="CAMPAIGN_A"
    )
    db_session.add(campaign1)
    db_session.commit()

    campaign2 = Campaign(
        campaign_name="Campaign B",
        campaign_date=date(2023, 1, 2),
        campaign_unique_identifier="CAMPAIGN_A" # Duplicate
    )
    db_session.add(campaign2)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()

def test_customer_offer_relationship_deletion(db_session):
    """Test cascade delete for Customer and its Offers."""
    customer = Customer(mobile_number="5555555555")
    db_session.add(customer)
    db_session.commit()

    offer1 = Offer(customer_id=customer.customer_id, offer_status="Active")
    offer2 = Offer(customer_id=customer.customer_id, offer_status="Expired")
    db_session.add_all([offer1, offer2])
    db_session.commit()

    customer_id = customer.customer_id
    offer1_id = offer1.offer_id
    offer2_id = offer2.offer_id

    # Ensure offers exist
    assert db_session.query(Offer).filter_by(customer_id=customer_id).count() == 2

    # Delete customer
    db_session.delete(customer)
    db_session.commit()

    # Check if customer is deleted
    assert db_session.query(Customer).filter_by(customer_id=customer_id).first() is None
    # Check if associated offers are deleted due to cascade
    assert db_session.query(Offer).filter_by(offer_id=offer1_id).first() is None
    assert db_session.query(Offer).filter_by(offer_id=offer2_id).first() is None

def test_offer_history_relationship_deletion(db_session):
    """Test cascade delete for Offer and its OfferHistory."""
    customer = Customer(mobile_number="6666666666")
    db_session.add(customer)
    db_session.commit()

    offer = Offer(customer_id=customer.customer_id, offer_status="Active")
    db_session.add(offer)
    db_session.commit()

    history1 = OfferHistory(offer_id=offer.offer_id, old_status="Active", new_status="Inactive")
    history2 = OfferHistory(offer_id=offer.offer_id, old_status="Inactive", new_status="Expired")
    db_session.add_all([history1, history2])
    db_session.commit()

    offer_id = offer.offer_id
    history1_id = history1.history_id
    history2_id = history2.history_id

    # Ensure history records exist
    assert db_session.query(OfferHistory).filter_by(offer_id=offer_id).count() == 2

    # Delete offer
    db_session.delete(offer)
    db_session.commit()

    # Check if offer is deleted
    assert db_session.query(Offer).filter_by(offer_id=offer_id).first() is None
    # Check if associated history records are deleted due to cascade
    assert db_session.query(OfferHistory).filter_by(history_id=history1_id).first() is None
    assert db_session.query(OfferHistory).filter_by(history_id=history2_id).first() is None

def test_event_relationships_deletion(db_session):
    """Test cascade delete for Customer/Offer and their Events."""
    customer = Customer(mobile_number="7777777777")
    db_session.add(customer)
    db_session.commit()

    offer = Offer(customer_id=customer.customer_id, offer_status="Active")
    db_session.add(offer)
    db_session.commit()

    event1 = Event(customer_id=customer.customer_id, event_type="LOGIN", source_system="LOS")
    event2 = Event(offer_id=offer.offer_id, event_type="CLICK", source_system="Moengage")
    db_session.add_all([event1, event2])
    db_session.commit()

    customer_id = customer.customer_id
    offer_id = offer.offer_id
    event1_id = event1.event_id
    event2_id = event2.event_id

    # Ensure events exist
    assert db_session.query(Event).filter_by(customer_id=customer_id).count() == 1
    assert db_session.query(Event).filter_by(offer_id=offer_id).count() == 1

    # Delete customer (should cascade delete event1)
    db_session.delete(customer)
    db_session.commit()

    assert db_session.query(Customer).filter_by(customer_id=customer_id).first() is None
    assert db_session.query(Event).filter_by(event_id=event1_id).first() is None
    # Offer and its event2 should still exist as offer was not deleted directly
    assert db_session.query(Offer).filter_by(offer_id=offer_id).first() is not None
    assert db_session.query(Event).filter_by(event_id=event2_id).first() is not None

    # Delete offer (should cascade delete event2)
    db_session.delete(offer)
    db_session.commit()

    assert db_session.query(Offer).filter_by(offer_id=offer_id).first() is None
    assert db_session.query(Event).filter_by(event_id=event2_id).first() is None

def test_offer_self_referencing_relationship(db_session):
    """Test the self-referencing relationship for original_offer_id."""
    customer = Customer(mobile_number="8888888888")
    db_session.add(customer)
    db_session.commit()

    original_offer = Offer(
        customer_id=customer.customer_id,
        offer_type="Fresh",
        offer_status="Active",
        source_offer_id="ORIGINAL1"
    )
    db_session.add(original_offer)
    db_session.commit()

    duplicate_offer = Offer(
        customer_id=customer.customer_id,
        offer_type="Enrich",
        offer_status="Inactive",
        source_offer_id="DUPLICATE1",
        is_duplicate=True,
        original_offer_id=original_offer.offer_id
    )
    db_session.add(duplicate_offer)
    db_session.commit()

    retrieved_original = db_session.query(Offer).filter_by(source_offer_id="ORIGINAL1").first()
    retrieved_duplicate = db_session.query(Offer).filter_by(source_offer_id="DUPLICATE1").first()

    assert retrieved_original is not None
    assert retrieved_duplicate is not None
    assert retrieved_duplicate.original_offer == retrieved_original
    assert retrieved_original.duplicate_offers == [retrieved_duplicate]
    assert retrieved_duplicate.is_duplicate is True
    assert retrieved_duplicate.original_offer_id == retrieved_original.offer_id