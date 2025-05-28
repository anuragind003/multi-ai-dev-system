import re
from datetime import datetime
import uuid

# --- Constants for Validation Rules ---

# Regex patterns
# Indian mobile numbers typically start with 6, 7, 8, or 9 and are 10 digits long.
MOBILE_NUMBER_PATTERN = re.compile(r"^[6-9]\d{9}$")
# Standard PAN format: 5 uppercase letters, 4 digits, 1 uppercase letter.
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
# Aadhaar reference number is a 12-digit number.
AADHAAR_PATTERN = re.compile(r"^\d{12}$")
# Standard UUID format.
UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

# Allowed values for enums/categories based on BRD and schema
ALLOWED_OFFER_STATUSES = {"Active", "Inactive", "Expired"}
ALLOWED_OFFER_TYPES = {"Fresh", "Enrich", "New-old", "New-new"}
ALLOWED_EVENT_TYPES = {
    "SMS_SENT", "SMS_DELIVERED", "SMS_CLICK", "CONVERSION",
    "APP_STAGE_LOGIN", "APP_STAGE_BUREAU_CHECK", "APP_STAGE_OFFER_DETAILS",
    "APP_STAGE_EKYC", "APP_STAGE_BANK_DETAILS", "APP_STAGE_OTHER_DETAILS",
    "APP_STAGE_ESIGN"
}
ALLOWED_EVENT_SOURCES = {"Moengage", "LOS"}
ALLOWED_FILE_TYPES = {"Prospect", "TW Loyalty", "Topup", "Employee loans"}
ALLOWED_CUSTOMER_SEGMENTS = {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"}

# Max lengths for string fields based on PostgreSQL schema
MAX_LENGTH_MOBILE = 20
MAX_LENGTH_PAN = 10
MAX_LENGTH_AADHAAR = 12
MAX_LENGTH_UCID = 50
MAX_LENGTH_LOAN_APP_NUMBER = 50 # Used for previous_loan_app_number and loan_application_number
MAX_LENGTH_OFFER_TYPE = 20
MAX_LENGTH_OFFER_STATUS = 20
MAX_LENGTH_PROPENSITY_FLAG = 50
MAX_LENGTH_ATTRIBUTION_CHANNEL = 50
MAX_LENGTH_EVENT_TYPE = 50
MAX_LENGTH_EVENT_SOURCE = 20
MAX_LENGTH_FILE_NAME = 255
MAX_LENGTH_UPLOADED_BY = 100
MAX_LENGTH_CAMPAIGN_IDENTIFIER = 100
MAX_LENGTH_CAMPAIGN_NAME = 255
MAX_LENGTH_CUSTOMER_SEGMENT = 10


# --- Basic Validation Functions ---

def is_not_empty(value) -> bool:
    """Checks if a value is not None and not an empty string after stripping whitespace."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True # For non-string types, just check if not None

def is_valid_length(value: str, max_len: int) -> bool:
    """Checks if a string value's length is within the maximum allowed length."""
    if value is None:
        return True # None values are considered valid length-wise if not required
    return len(str(value)) <= max_len

def is_valid_mobile_number(mobile: str) -> bool:
    """Validates an Indian mobile number format."""
    return bool(MOBILE_NUMBER_PATTERN.match(mobile))

def is_valid_pan(pan: str) -> bool:
    """Validates a PAN card number format."""
    return bool(PAN_PATTERN.match(pan))

def is_valid_aadhaar(aadhaar: str) -> bool:
    """Validates an Aadhaar reference number format."""
    return bool(AADHAAR_PATTERN.match(aadhaar))

def is_valid_uuid(uid: str) -> bool:
    """Validates a UUID format."""
    try:
        uuid.UUID(uid)
        return True
    except (ValueError, TypeError):
        return False

def is_valid_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
    """Validates a date string against a given format."""
    if not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False

def is_valid_timestamp(timestamp_str: str) -> bool:
    """
    Validates a timestamp string against common ISO 8601 formats.
    Supports 'YYYY-MM-DDTHH:MM:SS.fZ' and 'YYYY-MM-DDTHH:MM:SS'.
    """
    if not isinstance(timestamp_str, str):
        return False
    try:
        datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return True
    except ValueError:
        try:
            datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
            return True
        except ValueError:
            return False

def is_valid_enum(value: str, allowed_values: set) -> bool:
    """Checks if a value is within a set of allowed values (case-insensitive)."""
    if value is None:
        return False
    return str(value).strip().lower() in {v.lower() for v in allowed_values}

def is_boolean(value) -> bool:
    """Checks if a value can be interpreted as a boolean (True, False, 'true', 'false', 1, 0, '1', '0')."""
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return value in (0, 1)
    if isinstance(value, str):
        return value.lower() in ('true', 'false', '1', '0')
    return False

def is_integer(value) -> bool:
    """Checks if a value can be interpreted as an integer."""
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

def is_numeric(value) -> bool:
    """Checks if a value can be interpreted as a numeric type (int or float)."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

# --- Schema-based Validation Functions for specific contexts ---

def validate_lead_data(data: dict) -> tuple[bool, list]:
    """
    Validates data for the /api/leads endpoint.
    Required fields: mobile_number, loan_type, source_channel
    Optional fields: pan, application_id
    """
    errors = []

    # mobile_number (Required)
    mobile_number = data.get("mobile_number")
    if not is_not_empty(mobile_number):
        errors.append("mobile_number is required.")
    elif not is_valid_mobile_number(mobile_number):
        errors.append(f"mobile_number '{mobile_number}' is invalid.")
    elif not is_valid_length(mobile_number, MAX_LENGTH_MOBILE):
        errors.append(f"mobile_number exceeds maximum length of {MAX_LENGTH_MOBILE}.")

    # loan_type (Required)
    if not is_not_empty(data.get("loan_type")):
        errors.append("loan_type is required.")
    # No specific format for loan_type mentioned, assuming string.

    # source_channel (Required)
    if not is_not_empty(data.get("source_channel")):
        errors.append("source_channel is required.")
    # No specific format for source_channel mentioned, assuming string.

    # pan (Optional)
    pan = data.get("pan")
    if is_not_empty(pan):
        if not is_valid_pan(pan):
            errors.append(f"pan '{pan}' is invalid.")
        elif not is_valid_length(pan, MAX_LENGTH_PAN):
            errors.append(f"pan exceeds maximum length of {MAX_LENGTH_PAN}.")

    # application_id (Optional)
    application_id = data.get("application_id")
    if is_not_empty(application_id):
        if not is_valid_length(application_id, MAX_LENGTH_LOAN_APP_NUMBER):
            errors.append(f"application_id exceeds maximum length of {MAX_LENGTH_LOAN_APP_NUMBER}.")

    return not bool(errors), errors

def validate_eligibility_data(data: dict) -> tuple[bool, list]:
    """
    Validates data for the /api/eligibility endpoint.
    Required fields: mobile_number, loan_application_number, eligibility_status, offer_id
    """
    errors = []

    # mobile_number (Required)
    mobile_number = data.get("mobile_number")
    if not is_not_empty(mobile_number):
        errors.append("mobile_number is required.")
    elif not is_valid_mobile_number(mobile_number):
        errors.append(f"mobile_number '{mobile_number}' is invalid.")
    elif not is_valid_length(mobile_number, MAX_LENGTH_MOBILE):
        errors.append(f"mobile_number exceeds maximum length of {MAX_LENGTH_MOBILE}.")

    # loan_application_number (Required)
    loan_application_number = data.get("loan_application_number")
    if not is_not_empty(loan_application_number):
        errors.append("loan_application_number is required.")
    elif not is_valid_length(loan_application_number, MAX_LENGTH_LOAN_APP_NUMBER):
        errors.append(f"loan_application_number exceeds maximum length of {MAX_LENGTH_LOAN_APP_NUMBER}.")

    # eligibility_status (Required)
    if not is_not_empty(data.get("eligibility_status")):
        errors.append("eligibility_status is required.")
    # No specific format for eligibility_status mentioned, assuming string.

    # offer_id (Required)
    offer_id = data.get("offer_id")
    if not is_not_empty(offer_id):
        errors.append("offer_id is required.")
    elif not is_valid_uuid(offer_id):
        errors.append(f"offer_id '{offer_id}' is not a valid UUID.")

    return not bool(errors), errors

def validate_status_data(data: dict) -> tuple[bool, list]:
    """
    Validates data for the /api/status endpoint.
    Required fields: loan_application_number, application_stage, event_timestamp
    Optional fields: status_details
    """
    errors = []

    # loan_application_number (Required)
    loan_application_number = data.get("loan_application_number")
    if not is_not_empty(loan_application_number):
        errors.append("loan_application_number is required.")
    elif not is_valid_length(loan_application_number, MAX_LENGTH_LOAN_APP_NUMBER):
        errors.append(f"loan_application_number exceeds maximum length of {MAX_LENGTH_LOAN_APP_NUMBER}.")

    # application_stage (Required)
    application_stage = data.get("application_stage")
    if not is_not_empty(application_stage):
        errors.append("application_stage is required.")
    elif not is_valid_enum(application_stage, ALLOWED_EVENT_TYPES):
        errors.append(f"application_stage '{application_stage}' is not a recognized event type.")
    elif not is_valid_length(application_stage, MAX_LENGTH_EVENT_TYPE):
        errors.append(f"application_stage exceeds maximum length of {MAX_LENGTH_EVENT_TYPE}.")

    # event_timestamp (Required)
    event_timestamp = data.get("event_timestamp")
    if not is_not_empty(event_timestamp):
        errors.append("event_timestamp is required.")
    elif not is_valid_timestamp(event_timestamp):
        errors.append(f"event_timestamp '{event_timestamp}' is not a valid ISO 8601 timestamp.")

    # status_details (Optional)
    status_details = data.get("status_details")
    if status_details is not None and not isinstance(status_details, (str, dict)):
        errors.append("status_details must be a string or a JSON object.")
    # If status_details is a string, it should ideally have a max length, but schema is JSONB.
    # For JSONB, content validation is more complex and might be handled at a deeper level.

    return not bool(errors), errors

def validate_admin_upload_metadata(data: dict) -> tuple[bool, list]:
    """
    Validates metadata for the /api/admin/upload/customer-details endpoint.
    Required fields: file_type, file_content_base64, uploaded_by
    """
    errors = []

    # file_type (Required)
    file_type = data.get("file_type")
    if not is_not_empty(file_type):
        errors.append("file_type is required.")
    elif not is_valid_enum(file_type, ALLOWED_FILE_TYPES):
        errors.append(f"file_type '{file_type}' is not allowed. Must be one of {', '.join(ALLOWED_FILE_TYPES)}.")

    # file_content_base64 (Required)
    if not is_not_empty(data.get("file_content_base64")):
        errors.append("file_content_base64 is required.")
    # Decoding and further validation of base64 content (e.g., file type, size)
    # would typically happen in the service layer after this initial validation.

    # uploaded_by (Required)
    uploaded_by = data.get("uploaded_by")
    if not is_not_empty(uploaded_by):
        errors.append("uploaded_by is required.")
    elif not is_valid_length(uploaded_by, MAX_LENGTH_UPLOADED_BY):
        errors.append(f"uploaded_by exceeds maximum length of {MAX_LENGTH_UPLOADED_BY}.")

    return not bool(errors), errors

def validate_customer_data_row(row_data: dict, row_number: int = None) -> tuple[bool, list]:
    """
    Performs column-level validation for a single row of customer data from an uploaded file
    or batch ingestion. This is a comprehensive validation for customer and offer related fields.
    Assumes keys in row_data match database column names or expected input fields.
    """
    errors = []
    prefix = f"Row {row_number}: " if row_number is not None else ""

    # --- Customer Fields ---
    # mobile_number (Required)
    mobile_number = row_data.get("mobile_number")
    if not is_not_empty(mobile_number):
        errors.append(f"{prefix}mobile_number is required.")
    elif not is_valid_mobile_number(mobile_number):
        errors.append(f"{prefix}mobile_number '{mobile_number}' is invalid.")
    elif not is_valid_length(mobile_number, MAX_LENGTH_MOBILE):
        errors.append(f"{prefix}mobile_number exceeds max length {MAX_LENGTH_MOBILE}.")

    # pan (Optional)
    pan = row_data.get("pan")
    if is_not_empty(pan):
        if not is_valid_pan(pan):
            errors.append(f"{prefix}pan '{pan}' is invalid.")
        elif not is_valid_length(pan, MAX_LENGTH_PAN):
            errors.append(f"{prefix}pan exceeds max length {MAX_LENGTH_PAN}.")

    # aadhaar_ref_number (Optional)
    aadhaar_ref_number = row_data.get("aadhaar_ref_number")
    if is_not_empty(aadhaar_ref_number):
        if not is_valid_aadhaar(aadhaar_ref_number):
            errors.append(f"{prefix}aadhaar_ref_number '{aadhaar_ref_number}' is invalid.")
        elif not is_valid_length(aadhaar_ref_number, MAX_LENGTH_AADHAAR):
            errors.append(f"{prefix}aadhaar_ref_number exceeds max length {MAX_LENGTH_AADHAAR}.")

    # ucid (Optional)
    ucid = row_data.get("ucid")
    if is_not_empty(ucid):
        if not is_valid_length(ucid, MAX_LENGTH_UCID):
            errors.append(f"{prefix}ucid exceeds max length {MAX_LENGTH_UCID}.")

    # previous_loan_app_number (Optional)
    previous_loan_app_number = row_data.get("previous_loan_app_number")
    if is_not_empty(previous_loan_app_number):
        if not is_valid_length(previous_loan_app_number, MAX_LENGTH_LOAN_APP_NUMBER):
            errors.append(f"{prefix}previous_loan_app_number exceeds max length {MAX_LENGTH_LOAN_APP_NUMBER}.")

    # customer_segment (Optional, but if present, validate)
    customer_segment = row_data.get("customer_segment")
    if is_not_empty(customer_segment):
        if not is_valid_enum(customer_segment, ALLOWED_CUSTOMER_SEGMENTS):
            errors.append(f"{prefix}customer_segment '{customer_segment}' is invalid. Must be one of {', '.join(ALLOWED_CUSTOMER_SEGMENTS)}.")
        elif not is_valid_length(customer_segment, MAX_LENGTH_CUSTOMER_SEGMENT):
            errors.append(f"{prefix}customer_segment exceeds max length {MAX_LENGTH_CUSTOMER_SEGMENT}.")

    # is_dnd (Optional, boolean)
    is_dnd = row_data.get("is_dnd")
    if is_dnd is not None and not is_boolean(is_dnd):
        errors.append(f"{prefix}is_dnd must be a boolean value (e.g., True/False, 1/0, 'true'/'false').")

    # --- Offer Fields (if applicable in the upload, e.g., for offer data) ---
    # offer_type (Optional, but if present, validate)
    offer_type = row_data.get("offer_type")
    if is_not_empty(offer_type):
        if not is_valid_enum(offer_type, ALLOWED_OFFER_TYPES):
            errors.append(f"{prefix}offer_type '{offer_type}' is invalid. Must be one of {', '.join(ALLOWED_OFFER_TYPES)}.")
        elif not is_valid_length(offer_type, MAX_LENGTH_OFFER_TYPE):
            errors.append(f"{prefix}offer_type exceeds max length {MAX_LENGTH_OFFER_TYPE}.")

    # offer_status (Optional, but if present, validate)
    offer_status = row_data.get("offer_status")
    if is_not_empty(offer_status):
        if not is_valid_enum(offer_status, ALLOWED_OFFER_STATUSES):
            errors.append(f"{prefix}offer_status '{offer_status}' is invalid. Must be one of {', '.join(ALLOWED_OFFER_STATUSES)}.")
        elif not is_valid_length(offer_status, MAX_LENGTH_OFFER_STATUS):
            errors.append(f"{prefix}offer_status exceeds max length {MAX_LENGTH_OFFER_STATUS}.")

    # propensity_flag (Optional)
    propensity_flag = row_data.get("propensity_flag")
    if is_not_empty(propensity_flag):
        if not is_valid_length(propensity_flag, MAX_LENGTH_PROPENSITY_FLAG):
            errors.append(f"{prefix}propensity_flag exceeds max length {MAX_LENGTH_PROPENSITY_FLAG}.")

    # offer_start_date (Optional, date format)
    offer_start_date = row_data.get("offer_start_date")
    if is_not_empty(offer_start_date):
        if not is_valid_date(str(offer_start_date)):
            errors.append(f"{prefix}offer_start_date '{offer_start_date}' is not a valid date (YYYY-MM-DD).")

    # offer_end_date (Optional, date format)
    offer_end_date = row_data.get("offer_end_date")
    if is_not_empty(offer_end_date):
        if not is_valid_date(str(offer_end_date)):
            errors.append(f"{prefix}offer_end_date '{offer_end_date}' is not a valid date (YYYY-MM-DD).")

    # loan_application_number (Optional, distinct from previous_loan_app_number)
    loan_application_number = row_data.get("loan_application_number")
    if is_not_empty(loan_application_number):
        if not is_valid_length(loan_application_number, MAX_LENGTH_LOAN_APP_NUMBER):
            errors.append(f"{prefix}loan_application_number exceeds max length {MAX_LENGTH_LOAN_APP_NUMBER}.")

    # attribution_channel (Optional)
    attribution_channel = row_data.get("attribution_channel")
    if is_not_empty(attribution_channel):
        if not is_valid_length(attribution_channel, MAX_LENGTH_ATTRIBUTION_CHANNEL):
            errors.append(f"{prefix}attribution_channel exceeds max length {MAX_LENGTH_ATTRIBUTION_CHANNEL}.")

    return not bool(errors), errors