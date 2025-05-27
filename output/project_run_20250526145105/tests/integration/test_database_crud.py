import pytest
import os
from datetime import datetime, date
import uuid

from sqlalchemy import create_engine, Column, String, Boolean, Date, DateTime, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# Load environment variables for database connection
# In a real project, this would be handled by a config management system
# For testing, we can default to a test database or expect an env var.
DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/test_cdp_db")

Base = declarative_base()

# Define SQLAlchemy Models mirroring the database schema
class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True, nullable=True)
    pan_number = Column(String(10), unique=True, nullable=True)
    aadhaar_ref_number = Column(String(12), unique=True, nullable=True)
    ucid_number = Column(String(50), unique=True, nullable=True)
    previous_loan_app_number = Column(String(50), unique=True, nullable=True)
    customer_attributes = Column(JSONB, default={})
    customer_segments = Column(ARRAY(String), default=[])
    propensity_flag = Column(String(50), nullable=True)
    dnd_status = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    offers = relationship("Offer", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer(id={self.customer_id}, mobile={self.mobile_number})>"

class Offer(Base):
    __tablename__ = "offers"

    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False)
    offer_type = Column(String(50), nullable=True)
    offer_status = Column(String(50), nullable=True)
    product_type = Column(String(50), nullable=True)
    offer_details = Column(JSONB, default={})
    offer_start_date = Column(Date, nullable=True)
    offer_end_date = Column(Date, nullable=True)
    is_journey_started = Column(Boolean, default=False)
    loan_application_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    customer = relationship("Customer", back_populates="offers")

    def __repr__(self):
        return f"<Offer(id={self.offer_id}, customer_id={self.customer_id}, type={self.offer_type})>"

# Setup for tests
@pytest.fixture(scope="session")
def engine():
    """Provides a SQLAlchemy engine for the test database."""
    return create_engine(DATABASE_URL)

@pytest.fixture(scope="session")
def tables(engine):
    """Creates and drops tables for the test session."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def db_session(engine, tables):
    """Provides a transactional database session for each test function."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback() # Rollback changes after each test
    connection.close()

@pytest.fixture
def sample_customer_data():
    """Provides sample data for a customer."""
    return {
        "mobile_number": "9876543210",
        "pan_number": "ABCDE1234F",
        "aadhaar_ref_number": "123456789012",
        "customer_attributes": {"age": 30, "city": "Mumbai"},
        "customer_segments": ["C1", "High_Value"],
        "propensity_flag": "High",
        "dnd_status": False
    }

@pytest.fixture
def sample_offer_data(db_session):
    """Provides sample data for an offer, linked to a new customer."""
    customer = Customer(
        mobile_number="9999999999",
        pan_number="FGHIJ5678K",
        aadhaar_ref_number="987654321098"
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    return {
        "customer_id": customer.customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "product_type": "Preapproved",
        "offer_details": {"loan_amount": 100000, "interest_rate": 10.5},
        "offer_start_date": date(2024, 1, 1),
        "offer_end_date": date(2024, 12, 31),
        "is_journey_started": False
    }

# --- Integration Tests for Customer CRUD ---

def test_create_customer(db_session, sample_customer_data):
    """Test creating a new customer record."""
    customer = Customer(**sample_customer_data)
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    assert customer.customer_id is not None
    assert customer.mobile_number == sample_customer_data["mobile_number"]
    assert customer.pan_number == sample_customer_data["pan_number"]
    assert customer.customer_attributes == sample_customer_data["customer_attributes"]
    assert customer.customer_segments == sample_customer_data["customer_segments"]
    assert customer.created_at is not None
    assert customer.updated_at is not None

def test_read_customer(db_session, sample_customer_data):
    """Test reading an existing customer record."""
    customer = Customer(**sample_customer_data)
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    retrieved_customer = db_session.query(Customer).filter_by(customer_id=customer.customer_id).first()

    assert retrieved_customer is not None
    assert retrieved_customer.mobile_number == sample_customer_data["mobile_number"]
    assert retrieved_customer.pan_number == sample_customer_data["pan_number"]
    assert retrieved_customer.aadhaar_ref_number == sample_customer_data["aadhaar_ref_number"]
    assert retrieved_customer.customer_attributes == sample_customer_data["customer_attributes"]

def test_update_customer(db_session, sample_customer_data):
    """Test updating an existing customer record."""
    customer = Customer(**sample_customer_data)
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    new_mobile = "1122334455"
    customer.mobile_number = new_mobile
    customer.customer_attributes["occupation"] = "Engineer"
    db_session.commit()
    db_session.refresh(customer)

    updated_customer = db_session.query(Customer).filter_by(customer_id=customer.customer_id).first()

    assert updated_customer.mobile_number == new_mobile
    assert updated_customer.customer_attributes["occupation"] == "Engineer"
    assert updated_customer.updated_at > updated_customer.created_at # Check if updated_at changed

def test_delete_customer(db_session, sample_customer_data):
    """Test deleting a customer record."""
    customer = Customer(**sample_customer_data)
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    customer_id_to_delete = customer.customer_id
    db_session.delete(customer)
    db_session.commit()

    deleted_customer = db_session.query(Customer).filter_by(customer_id=customer_id_to_delete).first()
    assert deleted_customer is None

# --- Integration Tests for Offer CRUD ---

def test_create_offer(db_session, sample_offer_data):
    """Test creating a new offer record."""
    offer = Offer(**sample_offer_data)
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)

    assert offer.offer_id is not None
    assert offer.customer_id == sample_offer_data["customer_id"]
    assert offer.offer_type == sample_offer_data["offer_type"]
    assert offer.product_type == sample_offer_data["product_type"]
    assert offer.offer_details == sample_offer_data["offer_details"]
    assert offer.created_at is not None

def test_read_offer(db_session, sample_offer_data):
    """Test reading an existing offer record."""
    offer = Offer(**sample_offer_data)
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)

    retrieved_offer = db_session.query(Offer).filter_by(offer_id=offer.offer_id).first()

    assert retrieved_offer is not None
    assert retrieved_offer.customer_id == sample_offer_data["customer_id"]
    assert retrieved_offer.offer_status == sample_offer_data["offer_status"]
    assert retrieved_offer.offer_start_date == sample_offer_data["offer_start_date"]

def test_update_offer(db_session, sample_offer_data):
    """Test updating an existing offer record."""
    offer = Offer(**sample_offer_data)
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)

    new_status = "Expired"
    offer.offer_status = new_status
    offer.is_journey_started = True
    offer.loan_application_id = "LAN12345"
    db_session.commit()
    db_session.refresh(offer)

    updated_offer = db_session.query(Offer).filter_by(offer_id=offer.offer_id).first()

    assert updated_offer.offer_status == new_status
    assert updated_offer.is_journey_started is True
    assert updated_offer.loan_application_id == "LAN12345"
    assert updated_offer.updated_at > updated_offer.created_at

def test_delete_offer(db_session, sample_offer_data):
    """Test deleting an offer record."""
    offer = Offer(**sample_offer_data)
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)

    offer_id_to_delete = offer.offer_id
    db_session.delete(offer)
    db_session.commit()

    deleted_offer = db_session.query(Offer).filter_by(offer_id=offer_id_to_delete).first()
    assert deleted_offer is None

# --- Relationship Test ---

def test_customer_offer_relationship(db_session):
    """Test the one-to-many relationship between Customer and Offer."""
    customer_data = {
        "mobile_number": "1112223333",
        "pan_number": "RELAT4567P",
        "aadhaar_ref_number": "111122223333"
    }
    customer = Customer(**customer_data)
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    offer1_data = {
        "customer_id": customer.customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "product_type": "Loyalty",
        "offer_start_date": date(2024, 5, 1),
        "offer_end_date": date(2024, 11, 30)
    }
    offer2_data = {
        "customer_id": customer.customer_id,
        "offer_type": "Enrich",
        "offer_status": "Inactive",
        "product_type": "Top-up",
        "offer_start_date": date(2024, 6, 1),
        "offer_end_date": date(2024, 12, 31)
    }

    offer1 = Offer(**offer1_data)
    offer2 = Offer(**offer2_data)

    db_session.add_all([offer1, offer2])
    db_session.commit()
    db_session.refresh(customer)
    db_session.refresh(offer1)
    db_session.refresh(offer2)

    assert len(customer.offers) == 2
    assert offer1 in customer.offers
    assert offer2 in customer.offers
    assert offer1.customer.customer_id == customer.customer_id
    assert offer2.customer.customer_id == customer.customer_id

    # Test cascade delete
    customer_id_to_delete = customer.customer_id
    db_session.delete(customer)
    db_session.commit()

    deleted_customer = db_session.query(Customer).filter_by(customer_id=customer_id_to_delete).first()
    assert deleted_customer is None

    # Verify offers are also deleted
    deleted_offer1 = db_session.query(Offer).filter_by(offer_id=offer1.offer_id).first()
    deleted_offer2 = db_session.query(Offer).filter_by(offer_id=offer2.offer_id).first()
    assert deleted_offer1 is None
    assert deleted_offer2 is None