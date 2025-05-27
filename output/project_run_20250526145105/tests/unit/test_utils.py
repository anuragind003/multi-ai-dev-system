import pytest
from datetime import date, timedelta
import sys
import os

# Add the 'app' directory to the Python path to allow imports from app.utils
# This assumes the project structure is:
# project_root/
# ├── app/
# │   └── utils/
# │       └── common.py
# └── tests/
#     └── unit/
#         └── test_utils.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app')))

# Assuming these utility functions are defined in `app/utils/common.py`
# For the purpose of this test file, we assume `app/utils/common.py` contains:
# - is_valid_mobile_number(mobile_number: str) -> bool
# - is_valid_pan_number(pan_number: str) -> bool
# - determine_offer_status(offer_details: dict) -> str
# - determine_offer_type(new_offer_data: dict, existing_offers: list[dict]) -> str
# The actual implementation of these functions would be in `app/utils/common.py`.
from app.utils.common import (
    is_valid_mobile_number,
    is_valid_pan_number,
    determine_offer_status,
    determine_offer_type
)

# Test cases for is_valid_mobile_number (FR1, NFR3)
@pytest.mark.parametrize(
    "mobile_number, expected",
    [
        ("9876543210", True),  # Valid 10-digit number starting with 6-9
        ("6000000000", True),
        ("5999999999", False), # Starts with 5 (invalid prefix)
        ("1234567890", False), # Starts with 1 (invalid prefix)
        ("987654321", False),  # Too short
        ("98765432101", False), # Too long
        ("987654321A", False), # Contains non-digit character
        ("", False),          # Empty string
        (None, False),        # None input
        (1234567890, False),  # Not a string
    ],
)
def test_is_valid_mobile_number(mobile_number, expected):
    """
    Tests the validation logic for mobile numbers.
    """
    assert is_valid_mobile_number(mobile_number) == expected

# Test cases for is_valid_pan_number (FR1, NFR3)
@pytest.mark.parametrize(
    "pan_number, expected",
    [
        ("ABCDE1234F", True),  # Valid PAN format
        ("PQRST9876Z", True),
        ("abcde1234f", False), # Lowercase letters
        ("ABCDE1234", False),  # Too short
        ("ABCDE1234FG", False),# Too long
        ("ABCDE12345", False), # Last character not a letter
        ("ABCDE12A4F", False), # Letter in digit place
        ("1BCDE1234F", False), # Digit in letter place
        ("", False),          # Empty string
        (None, False),        # None input
        (1234567890, False),  # Not a string
    ],
)
def test_is_valid_pan_number(pan_number, expected):
    """
    Tests the validation logic for PAN numbers.
    """
    assert is_valid_pan_number(pan_number) == expected

# Test cases for determine_offer_status (FR18, FR51, FR53)
def test_determine_offer_status_active_no_journey():
    """
    Tests an offer that should be 'Active' because its end date is in the future
    and no loan journey has started. (FR18)
    """
    future_date = (date.today() + timedelta(days=30)).isoformat()
    offer_details = {
        'offer_end_date': future_date,
        'is_journey_started': False,
        'loan_application_id': None,
        'lan_validity_days': None,
        'status_override': None # No manual override
    }
    assert determine_offer_status(offer_details) == 'Active'

def test_determine_offer_status_expired_end_date_passed():
    """
    Tests an offer that should be 'Expired' because its end date has passed
    and no loan journey has started. (FR51)
    """
    past_date = (date.today() - timedelta(days=1)).isoformat()
    offer_details = {
        'offer_end_date': past_date,
        'is_journey_started': False,
        'loan_application_id': None,
        'lan_validity_days': None,
        'status_override': None
    }
    assert determine_offer_status(offer_details) == 'Expired'

def test_determine_offer_status_active_journey_started():
    """
    Tests an offer that should be 'Active' because a loan journey has started
    and its LAN validity is not yet over (mocked as not expired). (FR15, FR18)
    """
    future_date = (date.today() + timedelta(days=30)).isoformat()
    offer_details = {
        'offer_end_date': future_date,
        'is_journey_started': True,
        'loan_application_id': 'LAN123',
        'lan_validity_days': 90,
        'is_lan_expired': False, # Mocking this flag for the utility function
        'status_override': None
    }
    assert determine_offer_status(offer_details) == 'Active'

def test_determine_offer_status_expired_lan_validity_over():
    """
    Tests an offer that should be 'Expired' because a loan journey has started
    but its LAN validity period is over (mocked as expired). (FR53)
    """
    future_date = (date.today() + timedelta(days=30)).isoformat()
    offer_details = {
        'offer_end_date': future_date,
        'is_journey_started': True,
        'loan_application_id': 'LAN123',
        'lan_validity_days': 90,
        'is_lan_expired': True, # Mocking this flag for the utility function
        'status_override': None
    }
    assert determine_offer_status(offer_details) == 'Expired'

def test_determine_offer_status_inactive_override():
    """
    Tests an offer that is manually set to 'Inactive' regardless of other conditions. (FR18)
    """
    offer_details = {
        'offer_end_date': (date.today() + timedelta(days=30)).isoformat(),
        'is_journey_started': False,
        'status_override': 'Inactive'
    }
    assert determine_offer_status(offer_details) == 'Inactive'

def test_determine_offer_status_invalid_date_format():
    """
    Tests handling of an invalid date format for offer_end_date.
    Should default to 'Active' if no other expiry condition is met.
    """
    offer_details = {
        'offer_end_date': 'not-a-valid-date',
        'is_journey_started': False,
        'loan_application_id': None,
        'lan_validity_days': None,
        'status_override': None
    }
    assert determine_offer_status(offer_details) == 'Active'

# Test cases for determine_offer_type (FR19, FR20, FR21)
def test_determine_offer_type_fresh():
    """
    Tests when a new offer is 'Fresh' because there are no existing offers for the customer. (FR19)
    """
    new_offer = {'customer_id': 'cust1', 'product_type': 'Preapproved'}
    existing_offers = []
    assert determine_offer_type(new_offer, existing_offers) == 'Fresh'

def test_determine_offer_type_enrich_journey_not_started():
    """
    Tests when a new offer is 'Enrich' because an existing offer for the same product
    has no journey started. (FR20)
    """
    new_offer = {'customer_id': 'cust1', 'product_type': 'Preapproved'}
    existing_offers = [
        {'customer_id': 'cust1', 'product_type': 'Preapproved', 'is_journey_started': False, 'offer_id': 'offer_old'}
    ]
    assert determine_offer_type(new_offer, existing_offers) == 'Enrich'

def test_determine_offer_type_existing_journey_conflict():
    """
    Tests when a new offer conflicts with an existing offer for the same product
    where the journey has already started. (FR21)
    """
    new_offer = {'customer_id': 'cust1', 'product_type': 'Preapproved'}
    existing_offers = [
        {'customer_id': 'cust1', 'product_type': 'Preapproved', 'is_journey_started': True, 'offer_id': 'offer_old'}
    ]
    assert determine_offer_type(new_offer, existing_offers) == 'Existing-Journey-Conflict'

def test_determine_offer_type_fresh_different_product_type():
    """
    Tests when a new offer is 'Fresh' because existing offers are for different product types.
    """
    new_offer = {'customer_id': 'cust1', 'product_type': 'Top-up'}
    existing_offers = [
        {'customer_id': 'cust1', 'product_type': 'Preapproved', 'is_journey_started': False, 'offer_id': 'offer_old'}
    ]
    assert determine_offer_type(new_offer, existing_offers) == 'Fresh'

def test_determine_offer_type_fresh_different_customer():
    """
    Tests when a new offer is 'Fresh' because existing offers are for different customers.
    """
    new_offer = {'customer_id': 'cust2', 'product_type': 'Preapproved'}
    existing_offers = [
        {'customer_id': 'cust1', 'product_type': 'Preapproved', 'is_journey_started': False, 'offer_id': 'offer_old'}
    ]
    assert determine_offer_type(new_offer, existing_offers) == 'Fresh'

def test_determine_offer_type_multiple_existing_offers_enrich():
    """
    Tests when multiple existing offers are present, and one matches the 'Enrich' criteria.
    """
    new_offer = {'customer_id': 'cust1', 'product_type': 'Preapproved'}
    existing_offers = [
        {'customer_id': 'cust1', 'product_type': 'Top-up', 'is_journey_started': True, 'offer_id': 'offer_topup'},
        {'customer_id': 'cust1', 'product_type': 'Preapproved', 'is_journey_started': False, 'offer_id': 'offer_preapproved'}
    ]
    assert determine_offer_type(new_offer, existing_offers) == 'Enrich'

def test_determine_offer_type_multiple_existing_offers_conflict():
    """
    Tests when multiple existing offers are present, and one matches the 'Existing-Journey-Conflict' criteria.
    """
    new_offer = {'customer_id': 'cust1', 'product_type': 'Preapproved'}
    existing_offers = [
        {'customer_id': 'cust1', 'product_type': 'Top-up', 'is_journey_started': False, 'offer_id': 'offer_topup'},
        {'customer_id': 'cust1', 'product_type': 'Preapproved', 'is_journey_started': True, 'offer_id': 'offer_preapproved'}
    ]
    assert determine_offer_type(new_offer, existing_offers) == 'Existing-Journey-Conflict'