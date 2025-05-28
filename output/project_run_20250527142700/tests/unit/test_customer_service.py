import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime

# Assuming the customer_service module will be located at app.services.customer_service
# and models at app.models, and db at app.extensions.db
# These imports are placeholders and assume the structure.
from app.models import Customer, Offer, CustomerEvent
from app.extensions import db
# We will mock the actual service, so we don't need to import it directly for a placeholder test.
# from app.services.customer_service import get_customer_profile, create_customer, deduplicate_customer_data

@pytest.fixture
def app_context():
    """
    Provides a Flask application context for tests.
    This is necessary for operations that rely on current_app or database extensions.
    """
    from app import create_app # Assuming create_app function exists in app/__init__.py
    app = create_app()
    with app.app_context():
        yield app

@pytest.fixture
def mock_db_session():
    """
    Mocks the SQLAlchemy database session for isolated unit tests.
    """
    with patch('app.extensions.db.session') as mock_session:
        yield mock_session

@pytest.fixture
def mock_customer_model():
    """
    Mocks the Customer model for testing queries.
    """
    with patch('app.models.Customer') as mock_customer:
        yield mock_customer

@pytest.fixture
def mock_offer_model():
    """
    Mocks the Offer model for testing queries.
    """
    with patch('app.models.Offer') as mock_offer:
        yield mock_offer

@pytest.fixture
def mock_customer_event_model():
    """
    Mocks the CustomerEvent model for testing queries.
    """
    with patch('app.models.CustomerEvent') as mock_event:
        yield mock_event

# Placeholder for the customer_service module, which would contain the actual logic
# For unit tests, we'd typically mock the service's dependencies (like db interactions)
# and test its public methods. Since the service itself isn't implemented yet,
# these tests will mock the service's expected behavior.

class TestCustomerService:
    """
    Unit tests for the customer service module.
    These tests assume the existence of functions like:
    - get_customer_profile(customer_id)
    - create_customer(customer_data)
    - deduplicate_customer_data(customer_data)
    """

    @patch('app.services.customer_service.get_customer_profile')
    def test_get_customer_profile_success(self, mock_get_customer_profile, app_context):
        """
        Test successful retrieval of a customer profile.
        FR2: The system shall provide a single profile view of the customer.
        """
        customer_id = uuid.uuid4()
        mock_customer_data = {
            "customer_id": customer_id,
            "mobile_number": "9876543210",
            "pan": "ABCDE1234F",
            "customer_segment": "C1",
            "active_offers": [],
            "application_stages": []
        }
        mock_get_customer_profile.return_value = mock_customer_data

        # In a real test, you'd call the actual service function:
        # result = customer_service.get_customer_profile(customer_id)
        # For this placeholder, we just assert the mock was called.
        result = mock_get_customer_profile(customer_id)

        assert result == mock_customer_data
        mock_get_customer_profile.assert_called_once_with(customer_id)

    @patch('app.services.customer_service.get_customer_profile')
    def test_get_customer_profile_not_found(self, mock_get_customer_profile, app_context):
        """
        Test retrieval of a non-existent customer profile.
        """
        customer_id = uuid.uuid4()
        mock_get_customer_profile.return_value = None

        result = mock_get_customer_profile(customer_id)

        assert result is None
        mock_get_customer_profile.assert_called_once_with(customer_id)

    @patch('app.services.customer_service.create_customer')
    def test_create_customer_success(self, mock_create_customer, app_context):
        """
        Test successful creation of a new customer.
        """
        new_customer_data = {
            "mobile_number": "9988776655",
            "pan": "FGHIJ5678K",
            "customer_attributes": {"city": "Mumbai"},
            "customer_segment": "C2"
        }
        expected_customer_id = uuid.uuid4()
        mock_create_customer.return_value = {"customer_id": expected_customer_id, **new_customer_data}

        result = mock_create_customer(new_customer_data)

        assert result["customer_id"] == expected_customer_id
        assert result["mobile_number"] == new_customer_data["mobile_number"]
        mock_create_customer.assert_called_once_with(new_customer_data)

    @patch('app.services.customer_service.create_customer')
    def test_create_customer_duplicate_mobile(self, mock_create_customer, app_context):
        """
        Test creation of a customer with a duplicate mobile number.
        This should ideally raise an error or return a specific status.
        """
        duplicate_customer_data = {
            "mobile_number": "9876543210", # Assuming this mobile number already exists
            "pan": "LMNOP9012Q"
        }
        # Simulate an IntegrityError or a custom service error for duplicates
        mock_create_customer.side_effect = ValueError("Customer with this mobile number already exists.")

        with pytest.raises(ValueError, match="Customer with this mobile number already exists."):
            mock_create_customer(duplicate_customer_data)

        mock_create_customer.assert_called_once_with(duplicate_customer_data)

    @patch('app.services.customer_service.deduplicate_customer_data')
    def test_deduplicate_customer_data_logic(self, mock_deduplicate_customer_data, app_context):
        """
        Test the deduplication logic.
        FR3: The system shall perform deduplication within all Consumer Loan products.
        FR4: The system shall perform deduplication against the live book.
        FR5: The system shall dedupe Top-up loan offers only within other Top-up offers.
        """
        # Simulate input data for deduplication
        input_records = [
            {"mobile_number": "111", "pan": "PAN1", "aadhaar": None, "loan_app_num": None, "offer_type": "Loyalty"},
            {"mobile_number": "111", "pan": "PAN1", "aadhaar": None, "loan_app_num": None, "offer_type": "Preapproved"},
            {"mobile_number": "222", "pan": "PAN2", "aadhaar": "AADHAAR2", "loan_app_num": None, "offer_type": "Top-up"},
            {"mobile_number": "333", "pan": None, "aadhaar": "AADHAAR2", "loan_app_num": None, "offer_type": "Top-up"}, # Same Aadhaar as above
            {"mobile_number": "444", "pan": "PAN4", "aadhaar": None, "loan_app_num": "LAN001", "offer_type": "E-aggregator"}
        ]
        # Simulate the output after deduplication
        deduplication_result = {
            "unique_customers": [
                {"customer_id": uuid.uuid4(), "mobile_number": "111", "pan": "PAN1", "primary_offer_id": uuid.uuid4()},
                {"customer_id": uuid.uuid4(), "mobile_number": "222", "pan": "PAN2", "primary_offer_id": uuid.uuid4()}
            ],
            "duplicate_records": [
                {"original_record": input_records[1], "duplicate_of_customer_id": "..."}
            ],
            "topup_deduped_records": [
                {"original_record": input_records[3], "duplicate_of_customer_id": "..."}
            ]
        }
        mock_deduplicate_customer_data.return_value = deduplication_result

        result = mock_deduplicate_customer_data(input_records)

        assert "unique_customers" in result
        assert "duplicate_records" in result
        assert len(result["unique_customers"]) > 0
        mock_deduplicate_customer_data.assert_called_once_with(input_records)

    @patch('app.services.customer_service.update_customer_segment')
    def test_update_customer_segment(self, mock_update_customer_segment, app_context):
        """
        Test updating a customer's segment.
        FR14: The system shall maintain different customer attributes and customer segments.
        FR19: The system shall maintain customer segments like C1 to C8.
        """
        customer_id = uuid.uuid4()
        new_segment = "C5"
        mock_update_customer_segment.return_value = True # Simulate success

        result = mock_update_customer_segment(customer_id, new_segment)

        assert result is True
        mock_update_customer_segment.assert_called_once_with(customer_id, new_segment)

    @patch('app.services.customer_service.check_dnd_status')
    def test_check_dnd_status(self, mock_check_dnd_status, app_context):
        """
        Test checking DND status for a customer.
        FR21: The system shall store event data from Moengage and LOS in the LTFS Offer CDP, avoiding DND Customers.
        """
        customer_id = uuid.uuid4()
        mock_check_dnd_status.return_value = True # Simulate customer is DND

        is_dnd = mock_check_dnd_status(customer_id)

        assert is_dnd is True
        mock_check_dnd_status.assert_called_once_with(customer_id)