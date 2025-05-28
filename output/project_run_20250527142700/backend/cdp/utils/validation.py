import re
import uuid
from datetime import datetime, timezone

# --- Constants for Validation Rules ---

# Regex patterns for common identifiers
# Indian mobile numbers typically start with 6-9 and are 10 digits
MOBILE_NUMBER_PATTERN = re.compile(r"^[6-9]\d{9}$")
# Standard PAN format: 5 letters, 4 digits, 1 letter
PAN_NUMBER_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
# Aadhaar numbers are 12 digits
AADHAAR_NUMBER_PATTERN = re.compile(r"^\d{12}$")

# Max lengths as per database schema
UCID_NUMBER_MAX_LENGTH = 50
LOAN_APPLICATION_NUMBER_MAX_LENGTH = 100
SOURCE_OFFER_ID_MAX_LENGTH = 100

# Allowed values for categorical fields
SOURCE_SYSTEMS = ["Offermart", "E-aggregator", "Moengage", "LOS", "Customer 360", "MAS"]
OFFER_TYPES = ["Fresh", "Enrich", "New-old", "New-new"]
OFFER_STATUSES = ["Active", "Inactive", "Expired"]
# Based on FR21: "C1 to C8 and other analytics-prescribed segments" - only C1-C8 are explicitly mentioned.
CUSTOMER_SEGMENTS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]
# Based on FR25, FR26, FR27
EVENT_TYPES = [
    "SMS_SENT", "SMS_DELIVERED", "SMS_CLICK",
    "EKYC_ACHIEVED", "DISBURSEMENT",
    "JOURNEY_LOGIN", "BUREAU_CHECK", "OFFER_DETAILS", "BANK_DETAILS", "OTHER_DETAILS", "E_SIGN"
]

# --- Helper Validation Functions ---

def is_valid_uuid(val: str) -> bool:
    """Checks if a string is a valid UUID."""
    if not isinstance(val, str):
        return False
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False

def is_valid_mobile_number(number: str) -> bool:
    """Checks if a string is a valid 10-digit Indian mobile number."""
    if not isinstance(number, str):
        return False
    return bool(MOBILE_NUMBER_PATTERN.match(number))

def is_valid_pan_number(pan: str) -> bool:
    """Checks if a string is a valid PAN number."""
    if not isinstance(pan, str):
        return False
    return bool(PAN_NUMBER_PATTERN.match(pan))

def is_valid_aadhaar_number(aadhaar: str) -> bool:
    """Checks if a string is a valid 12-digit Aadhaar number."""
    if not isinstance(aadhaar, str):
        return False
    return bool(AADHAAR_NUMBER_PATTERN.match(aadhaar))

def is_valid_boolean(val) -> bool:
    """Checks if a value can be interpreted as a boolean (True, False, 1, 0, 'true', 'false')."""
    if isinstance(val, bool):
        return True
    if isinstance(val, (int, float)):
        return val in (0, 1)
    if isinstance(val, str):
        return val.lower() in ('true', 'false', '1', '0')
    return False

def is_valid_iso_timestamp(timestamp_str: str) -> bool:
    """
    Checks if a string is a valid ISO 8601 timestamp.
    Handles 'Z' for UTC by replacing it with '+00:00'.
    """
    if not isinstance(timestamp_str, str):
        return False
    try:
        # Replace 'Z' with '+00:00' for proper parsing of UTC timestamps
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False

def is_valid_date_format(date_str: str, fmt: str = '%Y-%m-%d') -> bool:
    """Checks if a string matches a specific date format."""
    if not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str, fmt).date()
        return True
    except ValueError:
        return False

def is_valid_jsonb(data) -> bool:
    """Checks if data is a dictionary, suitable for JSONB."""
    return isinstance(data, dict)

# --- Main Validation Functions for CDP Entities ---

def validate_customer_data(data: dict, is_new_record: bool = True) -> list[str]:
    """
    Validates incoming customer data for ingestion or update.
    Args:
        data (dict): The customer data payload.
        is_new_record (bool): True if validating for a new record (enforces more strict required fields).
    Returns:
        list[str]: A list of error messages.
    """
    errors = []

    # For new records, at least one primary identifier is required
    if is_new_record:
        if not (data.get('mobile_number') or data.get('pan_number') or
                data.get('aadhaar_number') or data.get('ucid_number')):
            errors.append("For a new customer, at least one of mobile_number, pan_number, aadhaar_number, or ucid_number is required.")

    # Validate specific fields if present
    if 'customer_id' in data and data['customer_id'] is not None:
        if not is_valid_uuid(str(data['customer_id'])):
            errors.append("Invalid customer_id format (must be a UUID).")

    if 'mobile_number' in data and data['mobile_number'] is not None:
        if not isinstance(data['mobile_number'], str) or (data['mobile_number'] and not is_valid_mobile_number(data['mobile_number'])):
            errors.append("Invalid mobile_number format or type.")

    if 'pan_number' in data and data['pan_number'] is not None:
        if not isinstance(data['pan_number'], str) or (data['pan_number'] and not is_valid_pan_number(data['pan_number'])):
            errors.append("Invalid pan_number format or type.")

    if 'aadhaar_number' in data and data['aadhaar_number'] is not None:
        if not isinstance(data['aadhaar_number'], str) or (data['aadhaar_number'] and not is_valid_aadhaar_number(data['aadhaar_number'])):
            errors.append("Invalid aadhaar_number format or type.")

    if 'ucid_number' in data and data['ucid_number'] is not None:
        if not isinstance(data['ucid_number'], str) or (data['ucid_number'] and len(data['ucid_number']) > UCID_NUMBER_MAX_LENGTH):
            errors.append(f"ucid_number must be a string and not exceed {UCID_NUMBER_MAX_LENGTH} characters.")

    if 'is_dnd' in data and data['is_dnd'] is not None:
        if not is_valid_boolean(data['is_dnd']):
            errors.append("is_dnd must be a boolean value.")

    if 'segment' in data and data['segment'] is not None:
        if not isinstance(data['segment'], str) or (data['segment'] and data['segment'] not in CUSTOMER_SEGMENTS):
            errors.append(f"Invalid customer segment. Must be one of: {', '.join(CUSTOMER_SEGMENTS)}.")

    if 'attributes' in data and data['attributes'] is not None:
        if not is_valid_jsonb(data['attributes']):
            errors.append("attributes must be a valid JSON object.")

    return errors

def validate_offer_data(data: dict, is_new_record: bool = True) -> list[str]:
    """
    Validates incoming offer data for ingestion or update.
    Args:
        data (dict): The offer data payload.
        is_new_record (bool): True if validating for a new record (enforces more strict required fields).
    Returns:
        list[str]: A list of error messages.
    """
    errors = []

    # Required fields for a new offer
    required_fields = ['customer_id', 'source_offer_id', 'offer_type', 'offer_status', 'valid_until', 'source_system']
    if is_new_record:
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}.")

    # Validate specific fields if present
    if 'offer_id' in data and data['offer_id'] is not None:
        if not is_valid_uuid(str(data['offer_id'])):
            errors.append("Invalid offer_id format (must be a UUID).")

    if 'customer_id' in data and data['customer_id'] is not None:
        if not is_valid_uuid(str(data['customer_id'])):
            errors.append("Invalid customer_id format (must be a UUID).")

    if 'source_offer_id' in data and data['source_offer_id'] is not None:
        if not isinstance(data['source_offer_id'], str) or (data['source_offer_id'] and len(data['source_offer_id']) > SOURCE_OFFER_ID_MAX_LENGTH):
            errors.append(f"source_offer_id must be a string and not exceed {SOURCE_OFFER_ID_MAX_LENGTH} characters.")

    if 'offer_type' in data and data['offer_type'] is not None:
        if not isinstance(data['offer_type'], str) or (data['offer_type'] and data['offer_type'] not in OFFER_TYPES):
            errors.append(f"Invalid offer_type. Must be one of: {', '.join(OFFER_TYPES)}.")

    if 'offer_status' in data and data['offer_status'] is not None:
        if not isinstance(data['offer_status'], str) or (data['offer_status'] and data['offer_status'] not in OFFER_STATUSES):
            errors.append(f"Invalid offer_status. Must be one of: {', '.join(OFFER_STATUSES)}.")

    if 'propensity' in data and data['propensity'] is not None:
        if not isinstance(data['propensity'], str): # Assuming propensity is a string as per schema
            errors.append("propensity must be a string.")

    if 'loan_application_number' in data and data['loan_application_number'] is not None:
        if not isinstance(data['loan_application_number'], str) or (data['loan_application_number'] and len(data['loan_application_number']) > LOAN_APPLICATION_NUMBER_MAX_LENGTH):
            errors.append(f"loan_application_number must be a string and not exceed {LOAN_APPLICATION_NUMBER_MAX_LENGTH} characters.")

    if 'valid_until' in data and data['valid_until'] is not None:
        if not is_valid_iso_timestamp(data['valid_until']):
            errors.append("Invalid valid_until format. Must be a valid ISO 8601 timestamp.")

    if 'source_system' in data and data['source_system'] is not None:
        if not isinstance(data['source_system'], str) or (data['source_system'] and data['source_system'] not in SOURCE_SYSTEMS):
            errors.append(f"Invalid source_system. Must be one of: {', '.join(SOURCE_SYSTEMS)}.")

    if 'channel' in data and data['channel'] is not None:
        if not isinstance(data['channel'], str): # Assuming channel is a string
            errors.append("channel must be a string.")

    if 'is_duplicate' in data and data['is_duplicate'] is not None:
        if not is_valid_boolean(data['is_duplicate']):
            errors.append("is_duplicate must be a boolean value.")

    if 'original_offer_id' in data and data['original_offer_id'] is not None:
        if not is_valid_uuid(str(data['original_offer_id'])):
            errors.append("Invalid original_offer_id format (must be a UUID).")

    return errors

def validate_event_data(data: dict, is_new_record: bool = True) -> list[str]:
    """
    Validates incoming event data.
    Args:
        data (dict): The event data payload.
        is_new_record (bool): True if validating for a new record (enforces more strict required fields).
    Returns:
        list[str]: A list of error messages.
    """
    errors = []

    required_fields = ['event_type', 'event_timestamp', 'source_system']
    if is_new_record:
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}.")

    if 'customer_id' in data and data['customer_id'] is not None:
        if not is_valid_uuid(str(data['customer_id'])):
            errors.append("Invalid customer_id format (must be a UUID).")

    if 'offer_id' in data and data['offer_id'] is not None:
        if not is_valid_uuid(str(data['offer_id'])):
            errors.append("Invalid offer_id format (must be a UUID).")

    if 'event_type' in data and data['event_type'] is not None:
        if not isinstance(data['event_type'], str) or (data['event_type'] and data['event_type'] not in EVENT_TYPES):
            errors.append(f"Invalid event_type. Must be one of: {', '.join(EVENT_TYPES)}.")

    if 'event_timestamp' in data and data['event_timestamp'] is not None:
        if not is_valid_iso_timestamp(data['event_timestamp']):
            errors.append("Invalid event_timestamp format. Must be a valid ISO 8601 timestamp.")

    if 'source_system' in data and data['source_system'] is not None:
        if not isinstance(data['source_system'], str) or (data['source_system'] and data['source_system'] not in SOURCE_SYSTEMS):
            errors.append(f"Invalid source_system. Must be one of: {', '.join(SOURCE_SYSTEMS)}.")

    if 'event_details' in data and data['event_details'] is not None:
        if not is_valid_jsonb(data['event_details']):
            errors.append("event_details must be a valid JSON object.")

    return errors

def validate_campaign_data(data: dict, is_new_record: bool = True) -> list[str]:
    """
    Validates incoming campaign data.
    Args:
        data (dict): The campaign data payload.
        is_new_record (bool): True if validating for a new record (enforces more strict required fields).
    Returns:
        list[str]: A list of error messages.
    """
    errors = []

    required_fields = ['campaign_name', 'campaign_date', 'campaign_unique_identifier']
    if is_new_record:
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}.")

    if 'campaign_id' in data and data['campaign_id'] is not None:
        if not is_valid_uuid(str(data['campaign_id'])):
            errors.append("Invalid campaign_id format (must be a UUID).")

    if 'campaign_name' in data and data['campaign_name'] is not None:
        if not isinstance(data['campaign_name'], str) or not data['campaign_name'].strip():
            errors.append("campaign_name must be a non-empty string.")

    if 'campaign_date' in data and data['campaign_date'] is not None:
        if not is_valid_date_format(data['campaign_date'], '%Y-%m-%d'):
            errors.append("Invalid campaign_date format. Must be YYYY-MM-DD.")

    if 'campaign_unique_identifier' in data and data['campaign_unique_identifier'] is not None:
        if not isinstance(data['campaign_unique_identifier'], str) or not data['campaign_unique_identifier'].strip():
            errors.append("campaign_unique_identifier must be a non-empty string.")

    # Numeric fields validation
    numeric_fields = {
        'attempted_count': int,
        'sent_count': int,
        'failed_count': int,
        'success_rate': (int, float),
        'conversion_rate': (int, float)
    }
    for field, expected_type in numeric_fields.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                errors.append(f"{field} must be a number.")
            elif data[field] < 0:
                errors.append(f"{field} must be non-negative.")
            if field in ['success_rate', 'conversion_rate'] and not (0 <= data[field] <= 100):
                errors.append(f"{field} must be between 0 and 100.")

    return errors