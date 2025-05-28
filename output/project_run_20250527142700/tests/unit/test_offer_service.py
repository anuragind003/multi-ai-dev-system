import pytest
from datetime import datetime, date, timedelta
import uuid

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

# Assuming models are defined in app.models
from app.models import Customer, Offer, CustomerEvent

# Assuming db is initialized in app.extensions
# This is a common Flask project structure.
from app.extensions import db

# Assuming the service to be tested is in app.services.offer_service
# This import will require the actual OfferService to be implemented.
# For the purpose of this test file, we assume its methods exist as tested.
from app.services.offer_service import OfferService


class TestConfig:
    """Configuration for the test Flask app."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # Use in-memory SQLite for fast unit tests
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True


@pytest.fixture(scope='session')
def app():
    """Fixture for a test Flask app instance with initialized database and models."""
    _app = Flask(__name__)
    _app.config.from_object(TestConfig)

    # Initialize SQLAlchemy with the app
    db.init_app(_app)

    with _app.app_context():
        db.create_all()  # Create tables for the in-memory SQLite database
        yield _app
        db.drop_all()  # Clean up after tests

@pytest.fixture(scope='function')
def client(app):
    """Fixture for a test client."""
    return app.test_client()

@pytest.fixture(scope='function')
def session(app):
    """
    Fixture for a database session, rolling back after each test.
    Ensures a clean state for each test function.
    """
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        # Bind the session to the connection and use it for the test
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)
        db.session = session
        yield session
        transaction.rollback()  # Rollback all changes
        connection.close()
        session.remove()


class TestOfferService:
    """Unit tests for the OfferService."""

    def test_create_offer(self, session):
        """Test creating a new offer (related to FR7, FR16)."""
        # Create a dummy customer first
        customer = Customer(
            mobile_number="9876543210",
            pan="ABCDE1234F",
            customer_segment="C1"
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)

        offer_data = {
            "customer_id": customer.customer_id,
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity_flag": "high_propensity",
            "offer_start_date": date.today(),
            "offer_end_date": date.today() + timedelta(days=30)
        }

        offer = OfferService.create_offer(session, **offer_data)

        assert offer is not None
        assert offer.customer_id == customer.customer_id
        assert offer.offer_type == "Fresh"
        assert offer.offer_status == "Active"
        assert session.query(Offer).count() == 1

    def test_update_offer_status(self, session):
        """Test updating an offer's status (related to FR15)."""
        customer = Customer(mobile_number="9876543211", pan="ABCDE1234G")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        offer = Offer(
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            offer_start_date=date.today(),
            offer_end_date=date.today() + timedelta(days=30)
        )
        session.add(offer)
        session.commit()
        session.refresh(offer)

        updated_offer = OfferService.update_offer_status(session, offer.offer_id, "Expired")

        assert updated_offer is not None
        assert updated_offer.offer_status == "Expired"
        assert session.query(Offer).filter_by(offer_id=offer.offer_id).first().offer_status == "Expired"

    def test_get_customer_offers(self, session):
        """Test retrieving all offers for a given customer."""
        customer = Customer(mobile_number="9876543212", pan="ABCDE1234H")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        offer1 = Offer(
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            offer_start_date=date.today(),
            offer_end_date=date.today() + timedelta(days=30)
        )
        offer2 = Offer(
            customer_id=customer.customer_id,
            offer_type="Enrich",
            offer_status="Inactive",
            offer_start_date=date.today() - timedelta(days=60),
            offer_end_date=date.today() - timedelta(days=30)
        )
        session.add_all([offer1, offer2])
        session.commit()

        offers = OfferService.get_customer_offers(session, customer.customer_id)

        assert len(offers) == 2
        assert all(o.customer_id == customer.customer_id for o in offers)

    def test_prevent_offer_modification_with_active_journey(self, session):
        """
        Test FR13: The system shall prevent modification of customer offers with started loan application journeys
        until the loan application is either expired or rejected.
        Assumes OfferService.update_offer_status raises a ValueError if modification is prevented.
        """
        customer = Customer(mobile_number="9876543213", pan="ABCDE1234I")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        offer = Offer(
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            offer_start_date=date.today(),
            offer_end_date=date.today() + timedelta(days=30),
            loan_application_number="LAN12345"  # Indicates journey started
        )
        session.add(offer)
        session.commit()
        session.refresh(offer)

        # Simulate an active application journey event
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type="APP_STAGE_LOGIN",
            event_source="LOS",
            event_details={"loan_application_number": "LAN12345"}
        )
        session.add(event)
        session.commit()

        with pytest.raises(ValueError, match="Offer cannot be modified due to active loan application journey"):
            OfferService.update_offer_status(session, offer.offer_id, "Inactive")

        # Verify status remains unchanged
        assert session.query(Offer).filter_by(offer_id=offer.offer_id).first().offer_status == "Active"

    def test_apply_attribution_logic(self, session):
        """
        Test FR20: The system shall apply attribution logic to determine which offer/channel prevails
        when a customer has multiple offers or comes through different channels.
        Assumes a priority: 'Insta' > 'E-aggregator' > 'Moengage'.
        """
        customer = Customer(mobile_number="9876543214", pan="ABCDE1234J")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        # Create multiple offers for the same customer
        offer1 = Offer(
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            offer_start_date=date.today(),
            offer_end_date=date.today() + timedelta(days=30),
            attribution_channel="Moengage"
        )
        offer2 = Offer(
            customer_id=customer.customer_id,
            offer_type="Enrich",
            offer_status="Active",
            offer_start_date=date.today(),
            offer_end_date=date.today() + timedelta(days=30),
            attribution_channel="E-aggregator"
        )
        offer3 = Offer(
            customer_id=customer.customer_id,
            offer_type="New-new",
            offer_status="Active",
            offer_start_date=date.today(),
            offer_end_date=date.today() + timedelta(days=30),
            attribution_channel="Insta"
        )
        session.add_all([offer1, offer2, offer3])
        session.commit()
        session.refresh(offer1)
        session.refresh(offer2)
        session.refresh(offer3)

        OfferService.apply_attribution_logic(session, customer.customer_id)

        # Re-fetch offers to check updated statuses
        offers_after_attribution = session.query(Offer).filter_by(customer_id=customer.customer_id).all()

        active_offer = next((o for o in offers_after_attribution if o.offer_status == "Active"), None)
        inactive_offers = [o for o in offers_after_attribution if o.offer_status == "Inactive"]

        assert active_offer is not None
        assert active_offer.attribution_channel == "Insta"  # Assuming Insta is highest priority
        assert len(inactive_offers) == 2  # The other two should be inactive

    def test_mark_offer_expired_by_date(self, session):
        """Test marking an offer as expired based on offer_end_date (FR37)."""
        customer = Customer(mobile_number="9876543215", pan="ABCDE1234K")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        offer = Offer(
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            offer_start_date=date.today() - timedelta(days=60),
            offer_end_date=date.today() - timedelta(days=1)  # Offer expired yesterday
        )
        session.add(offer)
        session.commit()
        session.refresh(offer)

        OfferService.mark_offers_expired_by_date(session)

        updated_offer = session.query(Offer).filter_by(offer_id=offer.offer_id).first()
        assert updated_offer.offer_status == "Expired"

    def test_mark_offer_expired_by_lan_validity(self, session):
        """Test marking an offer as expired based on LAN validity (FR38)."""
        customer = Customer(mobile_number="9876543216", pan="ABCDE1234L")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        offer = Offer(
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            offer_start_date=date.today() - timedelta(days=10),
            offer_end_date=date.today() + timedelta(days=30),
            loan_application_number="LAN98765"  # Journey started
        )
        session.add(offer)
        session.commit()
        session.refresh(offer)

        # Simulate a loan application event indicating expiry/rejection
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type="APP_STAGE_REJECTED",  # Or 'LOAN_EXPIRED'
            event_source="LOS",
            event_timestamp=datetime.now(),
            event_details={"loan_application_number": "LAN98765", "status": "Rejected"}
        )
        session.add(event)
        session.commit()

        OfferService.mark_offers_expired_by_lan_validity(session)

        updated_offer = session.query(Offer).filter_by(offer_id=offer.offer_id).first()
        assert updated_offer.offer_status == "Expired"

    def test_get_offer_history(self, session):
        """Test retrieving offer history for a customer (FR18, NFR3)."""
        customer = Customer(mobile_number="9876543217", pan="ABCDE1234M")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        # Create offers spanning more than 6 months
        offer1 = Offer(
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Expired",
            offer_start_date=date.today() - timedelta(days=200),
            offer_end_date=date.today() - timedelta(days=180),
            created_at=datetime.now() - timedelta(days=200)
        )
        offer2 = Offer(
            customer_id=customer.customer_id,
            offer_type="Enrich",
            offer_status="Inactive",
            offer_start_date=date.today() - timedelta(days=100),
            offer_end_date=date.today() - timedelta(days=80),
            created_at=datetime.now() - timedelta(days=100)
        )
        offer3 = Offer(
            customer_id=customer.customer_id,
            offer_type="New-new",
            offer_status="Active",
            offer_start_date=date.today() - timedelta(days=10),
            offer_end_date=date.today() + timedelta(days=20),
            created_at=datetime.now() - timedelta(days=10)
        )
        session.add_all([offer1, offer2, offer3])
        session.commit()

        # Assuming get_offer_history retrieves offers for the last 6 months (approx 180 days)
        history_offers = OfferService.get_offer_history(session, customer.customer_id)

        # offer1 should be excluded as its creation date is older than 6 months
        assert len(history_offers) == 2
        assert all(o.offer_id in [offer2.offer_id, offer3.offer_id] for o in history_offers)
        assert not any(o.offer_id == offer1.offer_id for o in history_offers)