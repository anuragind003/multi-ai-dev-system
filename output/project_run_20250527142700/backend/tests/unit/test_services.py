import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB # PostgreSQL specific types
from sqlalchemy.types import UUID, JSON # More generic types for testing with SQLite
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
import uuid
import io
import csv
from datetime import datetime, timedelta
import logging

# Configure logging for the test file
logging.basicConfig(level=logging.INFO)

# --- Mock/Minimal App and DB for Unit Testing ---
# This setup allows services to be tested in isolation without a full Flask app context
# or a persistent PostgreSQL database, using an in-memory SQLite for speed.

# Initialize a dummy SQLAlchemy instance for defining models in tests.
# This is a common pattern when you don't want to import the full app's db instance
# which might be tied to a specific app context or configuration.
# For unit tests, we want to control the database entirely.
test_db = SQLAlchemy()

# Attempt to import actual models from the backend application.
# If they are not available (e.g., during early development or isolated testing),
# define mock models that mirror the expected schema.
try:
    from backend.models import db, Customer, Offer, OfferHistory, Event, Campaign
    logging.info("Successfully imported models from backend.models.")
except ImportError:
    logging.warning("Could not import models from backend.models. Defining mock models for testing.")
    # Define dummy classes for local testing/linting without full Flask context
    # These mock models should mirror the structure of the actual models
    # using generic SQLAlchemy types compatible with SQLite for in-memory testing.

    Base = declarative_base()

    class MockCustomer(Base):
        __tablename__ = 'customers'
        customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        mobile_number = Column(String(20), unique=True)
        pan_number = Column(String(10), unique=True)
        aadhaar_number = Column(String(12), unique=True)
        ucid_number = Column(String(50), unique=True)
        customer_360_id = Column(String(50))
        is_dnd = Column(Boolean, default=False)
        segment = Column(String(50))
        attributes = Column(JSON) # Use generic JSON type for SQLite compatibility
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        offers = relationship("MockOffer", back_populates="customer")
        events = relationship("MockEvent", back_populates="customer")

        def __repr__(self):
            return f"<Customer {self.customer_id} - {self.mobile_number}>"

    class MockOffer(Base):
        __tablename__ = 'offers'
        offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
        source_offer_id = Column(String(100))
        offer_type = Column(String(50))
        offer_status = Column(String(50))
        propensity = Column(String(50))
        loan_application_number = Column(String(100))
        valid_until = Column(DateTime)
        source_system = Column(String(50))
        channel = Column(String(50))
        is_duplicate = Column(Boolean, default=False)
        original_offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id')) # Self-referencing
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        customer = relationship("MockCustomer", back_populates="offers")
        history = relationship("MockOfferHistory", back_populates="offer")
        events = relationship("MockEvent", back_populates="offer")
        duplicate_of = relationship("MockOffer", remote_side=[offer_id]) # For original_offer_id

        def __repr__(self):
            return f"<Offer {self.offer_id} - {self.offer_status}>"

    class MockOfferHistory(Base):
        __tablename__ = 'offer_history'
        history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'), nullable=False)
        status_change_date = Column(DateTime, default=datetime.utcnow)
        old_status = Column(String(50))
        new_status = Column(String(50))
        change_reason = Column(Text)

        offer = relationship("MockOffer", back_populates="history")

        def __repr__(self):
            return f"<OfferHistory {self.history_id} - {self.new_status}>"

    class MockEvent(Base):
        __tablename__ = 'events'
        event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'))
        offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id'))
        event_type = Column(String(100), nullable=False)
        event_timestamp = Column(DateTime, default=datetime.utcnow)
        source_system = Column(String(50), nullable=False)
        event_details = Column(JSON) # Use generic JSON type for SQLite compatibility

        customer = relationship("MockCustomer", back_populates="events")
        offer = relationship("MockOffer", back_populates="events")

        def __repr__(self):
            return f"<Event {self.event_id} - {self.event_type}>"

    class MockCampaign(Base):
        __tablename__ = 'campaigns'
        campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        campaign_name = Column(String(255), nullable=False)
        campaign_date = Column(DateTime, nullable=False) # Using DateTime for DATE type in SQLite
        campaign_unique_identifier = Column(String(100), unique=True, nullable=False)
        attempted_count = Column(Integer, default=0)
        sent_count = Column(Integer, default=0)
        failed_count = Column(Integer, default=0)
        success_rate = Column(Numeric(5,2), default=0.0)
        conversion_rate = Column(Numeric(5,2), default=0.0)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def __repr__(self):
            return f"<Campaign {self.campaign_id} - {self.campaign_name}>"

    # Assign mock models to the names expected by the tests
    Customer = MockCustomer
    Offer = MockOffer
    OfferHistory = MockOfferHistory
    Event = MockEvent
    Campaign = MockCampaign
    db = test_db # Use the test_db instance for mock models

# --- Pytest Fixtures ---

@pytest.fixture(scope='session')
def app():
    """Fixture for a minimal Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    # Use an in-memory SQLite database for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize db with the app
    db.init_app(app)

    with app.app_context():
        # Create all tables for the mock models
        db.create_all()
        yield app
        # Drop all tables after tests are done
        db.drop_all()

@pytest.fixture(scope='function')
def session(app):
    """Fixture for a database session for each test function."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        # Bind a session to the connection
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)

        # Replace the default session with our test session
        db.session = session

        yield session

        # Rollback the transaction after each test to ensure a clean slate
        transaction.rollback()
        connection.close()
        session.remove()

# --- Placeholder Service Classes ---
# These classes are placeholders. In a real scenario, you would import
# the actual service classes from `backend.services` and mock their dependencies.
# For now, they provide a structure for tests to interact with.

class MockCustomerService:
    def __init__(self, db_session):
        self.db_session = db_session

    def create_customer(self, data):
        customer = Customer(customer_id=uuid.uuid4(), **data)
        self.db_session.add(customer)
        self.db_session.commit()
        return customer

    def get_customer(self, customer_id):
        return self.db_session.query(Customer).get(customer_id)

    def update_customer_dnd(self, customer_id, is_dnd):
        customer = self.db_session.query(Customer).get(customer_id)
        if customer:
            customer.is_dnd = is_dnd
            self.db_session.commit()
            return True
        return False

class MockOfferService:
    def __init__(self, db_session):
        self.db_session = db_session

    def create_offer(self, data):
        offer = Offer(offer_id=uuid.uuid4(), **data)
        self.db_session.add(offer)
        self.db_session.commit()
        return offer

    def update_offer_status(self, offer_id, status):
        offer = self.db_session.query(Offer).get(offer_id)
        if offer:
            offer.offer_status = status
            self.db_session.commit()
            return True
        return False

    def get_active_offers_for_customer(self, customer_id):
        return self.db_session.query(Offer).filter_by(
            customer_id=customer_id, offer_status="Active"
        ).all()

class MockDeduplicationService:
    def __init__(self, db_session):
        self.db_session = db_session

    def deduplicate_customer_data(self, customer_data):
        # Simple mock deduplication: check if mobile or pan exists
        mobile = customer_data.get("mobile_number")
        pan = customer_data.get("pan_number")

        existing_customer = None
        if mobile:
            existing_customer = self.db_session.query(Customer).filter_by(mobile_number=mobile).first()
        if not existing_customer and pan:
            existing_customer = self.db_session.query(Customer).filter_by(pan_number=pan).first()

        if existing_customer:
            return {"is_duplicate": True, "master_id": existing_customer.customer_id}
        return {"is_duplicate": False, "master_id": None}

    def apply_deduplication_logic(self, new_offer, existing_offers):
        # Placeholder for complex attribution/deduplication logic
        # For testing, just return the new offer as is
        return new_offer

class MockIngestionService:
    def __init__(self, db_session):
        self.db_session = db_session

    def ingest_offermart_data(self, data):
        # Placeholder for data ingestion and validation
        if self.validate_data(data)["is_valid"]:
            # Simulate saving data
            logging.info(f"Ingesting Offermart data: {data}")
            return {"status": "success", "message": "Data ingested successfully"}
        return {"status": "failed", "message": "Validation failed"}

    def ingest_eaggregator_data(self, data):
        # Placeholder for real-time data ingestion
        if self.validate_data(data)["is_valid"]:
            logging.info(f"Ingesting E-aggregator data: {data}")
            return {"status": "success", "message": "Data ingested successfully"}
        return {"status": "failed", "message": "Validation failed"}

    def validate_data(self, data):
        # Basic mock validation
        if "customer_mobile" in data and data["customer_mobile"]:
            return {"is_valid": True, "errors": []}
        return {"is_valid": False, "errors": ["Missing customer_mobile"]}

class MockEventService:
    def __init__(self, db_session):
        self.db_session = db_session

    def record_moengage_event(self, data):
        # Simulate recording an event
        event = Event(
            event_id=uuid.uuid4(),
            customer_id=data.get("customer_id"),
            offer_id=data.get("offer_id"),
            event_type=data.get("event_type", "UNKNOWN"),
            source_system="Moengage",
            event_details=data.get("details", {})
        )
        self.db_session.add(event)
        self.db_session.commit()
        return {"status": "recorded", "event_id": event.event_id}

    def record_los_event(self, data):
        # Simulate recording an event
        event = Event(
            event_id=uuid.uuid4(),
            customer_id=data.get("customer_id"),
            offer_id=data.get("offer_id"),
            event_type=data.get("event_type", "UNKNOWN"),
            source_system="LOS",
            event_details=data.get("details", {})
        )
        self.db_session.add(event)
        self.db_session.commit()
        return {"status": "recorded", "event_id": event.event_id}

class MockExportService:
    def __init__(self, db_session):
        self.db_session = db_session

    def generate_moengage_file(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["customer_id", "mobile_number", "offer_id", "offer_type"])

        # Fetch non-DND customers with active offers
        customers = self.db_session.query(Customer).filter_by(is_dnd=False).all()
        for customer in customers:
            active_offers = self.db_session.query(Offer).filter_by(
                customer_id=customer.customer_id, offer_status="Active"
            ).all()
            for offer in active_offers:
                writer.writerow([
                    str(customer.customer_id),
                    customer.mobile_number,
                    str(offer.offer_id),
                    offer.offer_type
                ])
        output.seek(0)
        return output

    def generate_duplicate_file(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["customer_id", "mobile_number", "pan_number", "is_duplicate", "master_id"])
        # Simulate fetching duplicate data
        duplicates = self.db_session.query(Customer).filter(Customer.is_dnd == False).limit(2).all() # Example
        for dup in duplicates:
            writer.writerow([str(dup.customer_id), dup.mobile_number, dup.pan_number, True, str(uuid.uuid4())])
        output.seek(0)
        return output

    def generate_unique_file(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["customer_id", "mobile_number", "pan_number", "segment"])
        # Simulate fetching unique data
        uniques = self.db_session.query(Customer).filter(Customer.is_dnd == False).limit(2).all() # Example
        for unique in uniques:
            writer.writerow([str(unique.customer_id), unique.mobile_number, unique.pan_number, unique.segment])
        output.seek(0)
        return output

    def generate_error_file(self):
        output = io.StringIO()
        # For Excel, openpyxl would be used, but for simplicity in unit test, use CSV
        writer = csv.writer(output)
        writer.writerow(["row_number", "error_message", "raw_data"])
        # Simulate fetching error data
        writer.writerow([1, "Invalid mobile number", "{'mobile': 'abc'}"])
        output.seek(0)
        return output

# --- Unit Tests for Services ---

def test_customer_service_create_customer(session):
    """Test creating a new customer."""
    service = MockCustomerService(session)
    customer_data = {
        "mobile_number": "9876543210",
        "pan_number": "ABCDE1234F",
        "segment": "C1"
    }
    customer = service.create_customer(customer_data)

    retrieved_customer = session.query(Customer).filter_by(mobile_number="9876543210").first()
    assert retrieved_customer is not None
    assert retrieved_customer.pan_number == "ABCDE1234F"
    assert retrieved_customer.segment == "C1"
    assert retrieved_customer.is_dnd is False

def test_customer_service_update_dnd_status(session):
    """Test updating a customer's DND status."""
    service = MockCustomerService(session)
    customer = Customer(mobile_number="1111111111", pan_number="PQRST1234A", is_dnd=False)
    session.add(customer)
    session.commit()
    customer_id = customer.customer_id

    success = service.update_customer_dnd(customer_id, True)
    assert success is True
    session.refresh(customer) # Refresh the object to get the latest state from the DB
    assert customer.is_dnd is True

def test_offer_service_create_offer(session):
    """Test creating a new offer."""
    service = MockOfferService(session)
    customer = Customer(mobile_number="2222222222", pan_number="UVWXY5678B")
    session.add(customer)
    session.commit()
    customer_id = customer.customer_id

    offer_data = {
        "customer_id": customer_id,
        "offer_type": "Fresh",
        "offer_status": "Active",
        "source_system": "Offermart",
        "valid_until": datetime.utcnow() + timedelta(days=30)
    }
    offer = service.create_offer(offer_data)

    retrieved_offer = session.query(Offer).filter_by(customer_id=customer_id, offer_type="Fresh").first()
    assert retrieved_offer is not None
    assert retrieved_offer.offer_status == "Active"
    assert retrieved_offer.source_system == "Offermart"

def test_offer_service_update_offer_status(session):
    """Test updating an offer's status."""
    service = MockOfferService(session)
    customer = Customer(mobile_number="3333333333", pan_number="ABCDE9876Z")
    session.add(customer)
    session.commit()

    offer = Offer(customer_id=customer.customer_id, offer_type="Fresh", offer_status="Active", source_system="Offermart")
    session.add(offer)
    session.commit()
    offer_id = offer.offer_id

    success = service.update_offer_status(offer_id, "Expired")
    assert success is True
    session.refresh(offer)
    assert offer.offer_status == "Expired"

def test_deduplication_service_new_customer(session):
    """Test deduplication for a new, unique customer."""
    service = MockDeduplicationService(session)
    customer_data = {"mobile_number": "4444444444", "pan_number": "FGHIJ1111K"}
    result = service.deduplicate_customer_data(customer_data)
    assert result["is_duplicate"] is False
    assert result["master_id"] is None

def test_deduplication_service_existing_customer_by_mobile(session):
    """Test deduplication for an existing customer matching by mobile."""
    service = MockDeduplicationService(session)
    existing_customer = Customer(mobile_number="5555555555", pan_number="KLMNO2222L")
    session.add(existing_customer)
    session.commit()

    customer_data = {"mobile_number": "5555555555"} # Match by mobile
    result = service.deduplicate_customer_data(customer_data)
    assert result["is_duplicate"] is True
    assert result["master_id"] == existing_customer.customer_id

def test_deduplication_service_existing_customer_by_pan(session):
    """Test deduplication for an existing customer matching by PAN."""
    service = MockDeduplicationService(session)
    existing_customer = Customer(mobile_number="6666666666", pan_number="PQRST3333M")
    session.add(existing_customer)
    session.commit()

    customer_data = {"pan_number": "PQRST3333M"} # Match by pan
    result = service.deduplicate_customer_data(customer_data)
    assert result["is_duplicate"] is True
    assert result["master_id"] == existing_customer.customer_id

def test_ingestion_service_offermart_data_valid(session):
    """Test ingestion of valid Offermart data."""
    service = MockIngestionService(session)
    data = {"customer_mobile": "7777777777", "offer_amount": 100000}
    result = service.ingest_offermart_data(data)
    assert result["status"] == "success"

def test_ingestion_service_offermart_data_invalid(session):
    """Test ingestion of invalid Offermart data."""
    service = MockIngestionService(session)
    data = {"offer_amount": 100000} # Missing mobile number
    result = service.ingest_offermart_data(data)
    assert result["status"] == "failed"
    assert "Missing customer_mobile" in result["message"]

def test_event_service_record_moengage_event(session):
    """Test recording a Moengage event."""
    service = MockEventService(session)
    customer = Customer(mobile_number="8888888888", pan_number="UVWXY4444N")
    session.add(customer)
    session.commit()

    event_data = {
        "customer_id": customer.customer_id,
        "event_type": "SMS_SENT",
        "campaign_id": "campaign_123",
        "details": {"message": "Offer sent"}
    }
    result = service.record_moengage_event(event_data)
    assert result["status"] == "recorded"
    assert result["event_id"] is not None

    retrieved_event = session.query(Event).get(result["event_id"])
    assert retrieved_event is not None
    assert retrieved_event.event_type == "SMS_SENT"
    assert retrieved_event.source_system == "Moengage"

def test_export_service_generate_moengage_file_excludes_dnd(session):
    """Test generation of Moengage-formatted file, ensuring DND customers are excluded."""
    service = MockExportService(session)

    customer1 = Customer(mobile_number="9000000001", pan_number="TEST10001A", is_dnd=False)
    customer2 = Customer(mobile_number="9000000002", pan_number="TEST10002B", is_dnd=True) # DND customer
    session.add_all([customer1, customer2])
    session.commit()

    offer1 = Offer(customer_id=customer1.customer_id, offer_type="Fresh", offer_status="Active", source_system="Offermart")
    offer2 = Offer(customer_id=customer2.customer_id, offer_type="Preapproved", offer_status="Active", source_system="Offermart")
    session.add_all([offer1, offer2])
    session.commit()

    file_content_io = service.generate_moengage_file()
    content = file_content_io.getvalue()

    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    assert len(rows) == 2 # Header + 1 non-DND customer row
    assert rows[0] == ["customer_id", "mobile_number", "offer_id", "offer_type"]
    assert "9000000001" in rows[1] # Should include non-DND customer
    assert "9000000002" not in content # Should exclude DND customer

def test_export_service_generate_duplicate_file(session):
    """Test generation of duplicate data file."""
    service = MockExportService(session)
    customer1 = Customer(mobile_number="9000000003", pan_number="TEST10003C")
    customer2 = Customer(mobile_number="9000000004", pan_number="TEST10004D")
    session.add_all([customer1, customer2])
    session.commit()

    file_content_io = service.generate_duplicate_file()
    content = file_content_io.getvalue()
    assert "customer_id" in content
    assert "is_duplicate" in content
    # Further assertions would involve parsing and checking specific mock data

def test_export_service_generate_unique_file(session):
    """Test generation of unique data file."""
    service = MockExportService(session)
    customer1 = Customer(mobile_number="9000000005", pan_number="TEST10005E")
    customer2 = Customer(mobile_number="9000000006", pan_number="TEST10006F")
    session.add_all([customer1, customer2])
    session.commit()

    file_content_io = service.generate_unique_file()
    content = file_content_io.getvalue()
    assert "customer_id" in content
    assert "segment" in content
    # Further assertions would involve parsing and checking specific mock data

def test_export_service_generate_error_file(session):
    """Test generation of error data file."""
    service = MockExportService(session)
    file_content_io = service.generate_error_file()
    content = file_content_io.getvalue()
    assert "row_number" in content
    assert "error_message" in content
    assert "raw_data" in content
    assert "Invalid mobile number" in content