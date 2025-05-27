import re
from datetime import datetime
import uuid

# --- Common Validation Functions ---


def is_valid_uuid(value):
    """Checks if a string is a valid UUID."""
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def is_valid_mobile_number(value):
    """Checks if a string is a valid 10-digit mobile number.
    Assumes Indian mobile numbers: 10 digits, starts with 6, 7, 8, or 9.
    """
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r'^[6-9]\d{9}$', value))


def is_valid_pan_number(value):
    """Checks if a string is a valid PAN number (e.g., ABCDE1234F).
    Format: 5 letters, 4 digits, 1 letter.
    """
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', value.upper()))


def is_valid_aadhaar_number(value):
    """Checks if a string is a valid 12-digit Aadhaar number."""
    if not isinstance(value, str):
        return False
    return bool(re.fullmatch(r'^\d{12}$', value))


def is_valid_date(value):
    """Checks if a string is a valid date in YYYY-MM-DD format."""
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, '%Y-%m-%d').date()
        return True
    except ValueError:
        return False


def is_valid_datetime(value):
    """Checks if a string is a valid datetime in ISO format
    (e.g., YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS).
    """
    if not isinstance(value, str):
        return False
    try:
        # Python's datetime.fromisoformat handles various ISO 8601 formats
        datetime.fromisoformat(value)
        return True
    except ValueError:
        # Fallback for common non-ISO format if necessary
        try:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False


def is_valid_boolean(value):
    """Checks if a value is a boolean."""
    return isinstance(value, bool)


def is_valid_positive_number(value):
    """Checks if a value is a positive integer or float."""
    return isinstance(value, (int, float)) and value > 0


def is_valid_enum(value, allowed_values):
    """Checks if a value is within a list of allowed values
    (case-insensitive for strings).
    """
    if isinstance(value, str):
        return value.lower() in [v.lower() for v in allowed_values]
    return value in allowed_values


def validate_required_fields(data, required_fields):
    """Checks if all required fields are present in the data."""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return False, {"missing_fields": missing_fields}
    return True, {}


# --- Specific Payload Validation Functions for API Endpoints ---


def validate_leads_payload(data):
    """Validates the payload for the /api/leads endpoint."""
    errors = {}

    # Required fields check
    required_fields = ["mobile_number", "loan_type", "source_channel"]
    is_present, missing_errors = validate_required_fields(data, required_fields)
    if not is_present:
        errors.update(missing_errors)
        return False, errors

    # Type and format validations
    if not is_valid_mobile_number(data.get("mobile_number")):
        errors["mobile_number"] = ("Invalid or missing mobile_number. "
                                   "Must be a 10-digit string.")

    if "pan_number" in data and not is_valid_pan_number(data["pan_number"]):
        errors["pan_number"] = "Invalid PAN number format."

    if "aadhaar_number" in data and \
            not is_valid_aadhaar_number(data["aadhaar_number"]):
        errors["aadhaar_number"] = "Invalid Aadhaar number format."

    allowed_loan_types = [
        "Prospect", "TW Loyalty", "Topup", "Employee loans",
        "Preapproved", "E-aggregator"
    ]
    if not is_valid_enum(data.get("loan_type"), allowed_loan_types):
        errors["loan_type"] = (f"Invalid loan_type. Must be one of "
                               f"{', '.join(allowed_loan_types)}.")

    if not isinstance(data.get("source_channel"), str) or \
            not data.get("source_channel").strip():
        errors["source_channel"] = ("Invalid or empty source_channel. "
                                    "Must be a non-empty string.")

    return not bool(errors), errors


def validate_eligibility_payload(data):
    """Validates the payload for the /api/eligibility endpoint."""
    errors = {}

    required_fields = ["customer_id", "offer_id",
                       "eligibility_status", "loan_amount"]
    is_present, missing_errors = validate_required_fields(data, required_fields)
    if not is_present:
        errors.update(missing_errors)
        return False, errors

    if not is_valid_uuid(data.get("customer_id")):
        errors["customer_id"] = ("Invalid or missing customer_id. "
                                 "Must be a valid UUID.")

    if not is_valid_uuid(data.get("offer_id")):
        errors["offer_id"] = ("Invalid or missing offer_id. "
                              "Must be a valid UUID.")

    allowed_eligibility_statuses = ["Eligible", "Not Eligible",
                                    "Pending", "Approved", "Rejected"]
    if not is_valid_enum(data.get("eligibility_status"),
                         allowed_eligibility_statuses):
        errors["eligibility_status"] = (f"Invalid eligibility_status. "
                                        f"Must be one of "
                                        f"{', '.join(allowed_eligibility_statuses)}.")

    if not is_valid_positive_number(data.get("loan_amount")):
        errors["loan_amount"] = "Invalid loan_amount. Must be a positive number."

    return not bool(errors), errors


def validate_status_update_payload(data):
    """Validates the payload for the /api/status-updates endpoint."""
    errors = {}

    required_fields = ["loan_application_number", "customer_id",
                       "current_stage", "status_timestamp"]
    is_present, missing_errors = validate_required_fields(data, required_fields)
    if not is_present:
        errors.update(missing_errors)
        return False, errors

    if not isinstance(data.get("loan_application_number"), str) or \
            not data.get("loan_application_number").strip():
        errors["loan_application_number"] = ("Invalid or empty "
                                             "loan_application_number. "
                                             "Must be a non-empty string.")

    if not is_valid_uuid(data.get("customer_id")):
        errors["customer_id"] = ("Invalid or missing customer_id. "
                                 "Must be a valid UUID.")

    allowed_stages = [
        "login", "bureau check", "offer details", "eKYC", "Bank details",
        "other details", "e-sign", "Disbursed", "Rejected", "Expired"
    ]
    if not is_valid_enum(data.get("current_stage"), allowed_stages):
        errors["current_stage"] = (f"Invalid current_stage. Must be one of "
                                   f"{', '.join(allowed_stages)}.")

    if not is_valid_datetime(data.get("status_timestamp")):
        errors["status_timestamp"] = ("Invalid status_timestamp. "
                                      "Must be a valid ISO 8601 datetime string.")

    return not bool(errors), errors


def validate_customer_upload_payload(data):
    """Validates the payload for the /admin/customer-data/upload endpoint (metadata)."""
    errors = {}

    required_fields = ["file_content", "file_name", "loan_type"]
    is_present, missing_errors = validate_required_fields(data, required_fields)
    if not is_present:
        errors.update(missing_errors)
        return False, errors

    if not isinstance(data.get("file_content"), str) or \
            not data.get("file_content").strip():
        errors["file_content"] = ("Invalid or empty file_content. "
                                  "Must be a non-empty base64 encoded string.")

    if not isinstance(data.get("file_name"), str) or \
            not data.get("file_name").strip():
        errors["file_name"] = ("Invalid or empty file_name. "
                               "Must be a non-empty string.")

    allowed_loan_types = ["Prospect", "TW Loyalty", "Topup", "Employee loans"]
    if not is_valid_enum(data.get("loan_type"), allowed_loan_types):
        errors["loan_type"] = (f"Invalid loan_type. Must be one of "
                               f"{', '.join(allowed_loan_types)}.")

    return not bool(errors), errors


# --- Validation Functions for Internal Data Structures (e.g., file rows) ---


def validate_customer_data_row(row_data):
    """
    Validates a single row of customer data, typically from a file upload.
    """
    errors = {}

    if "mobile_number" not in row_data or \
            not is_valid_mobile_number(row_data["mobile_number"]):
        errors["mobile_number"] = ("Invalid or missing mobile_number. "
                                   "Must be a 10-digit string.")

    if "pan_number" in row_data and \
            not is_valid_pan_number(row_data["pan_number"]):
        errors["pan_number"] = "Invalid PAN number format."

    if "aadhaar_number" in row_data and \
            not is_valid_aadhaar_number(row_data["aadhaar_number"]):
        errors["aadhaar_number"] = "Invalid Aadhaar number format."

    if "ucid_number" in row_data and \
            not isinstance(row_data["ucid_number"], str):
        errors["ucid_number"] = "UCID number must be a string."

    if "loan_application_number" in row_data and \
            not isinstance(row_data["loan_application_number"], str):
        errors["loan_application_number"] = ("Loan application number "
                                             "must be a string.")

    if "dnd_flag" in row_data and not is_valid_boolean(row_data["dnd_flag"]):
        errors["dnd_flag"] = "DND flag must be a boolean."

    if "segment" in row_data and not isinstance(row_data["segment"], str):
        errors["segment"] = "Segment must be a string."

    return not bool(errors), errors


def validate_offer_data_row(row_data):
    """
    Validates a single row of offer data.
    """
    errors = {}

    required_fields = ["customer_id", "offer_type",
                       "offer_status", "start_date", "end_date"]
    is_present, missing_errors = validate_required_fields(row_data, required_fields)
    if not is_present:
        errors.update(missing_errors)
        return False, errors

    if not is_valid_uuid(row_data.get("customer_id")):
        errors["customer_id"] = "Invalid customer_id. Must be a valid UUID."

    allowed_offer_types = ["Fresh", "Enrich", "New-old", "New-new"]
    if not is_valid_enum(row_data.get("offer_type"), allowed_offer_types):
        errors["offer_type"] = (f"Invalid offer_type. Must be one of "
                                f"{', '.join(allowed_offer_types)}.")

    allowed_offer_statuses = ["Active", "Inactive", "Expired"]
    if not is_valid_enum(row_data.get("offer_status"), allowed_offer_statuses):
        errors["offer_status"] = (f"Invalid offer_status. Must be one of "
                                  f"{', '.join(allowed_offer_statuses)}.")

    if "propensity" in row_data and \
            not isinstance(row_data["propensity"], str):
        errors["propensity"] = "Propensity must be a string."

    if not is_valid_date(row_data.get("start_date")):
        errors["start_date"] = "Invalid start_date. Must be in YYYY-MM-DD format."

    if not is_valid_date(row_data.get("end_date")):
        errors["end_date"] = "Invalid end_date. Must be in YYYY-MM-DD format."
    elif is_valid_date(row_data.get("start_date")) and \
            is_valid_date(row_data.get("end_date")):
        try:
            start_dt = datetime.strptime(row_data["start_date"], '%Y-%m-%d').date()
            end_dt = datetime.strptime(row_data["end_date"], '%Y-%m-%d').date()
            if end_dt < start_dt:
                errors["end_date"] = "End date cannot be before start date."
        except ValueError:
            # This case should ideally be caught by is_valid_date
            pass

    if "channel" in row_data and not isinstance(row_data["channel"], str):
        errors["channel"] = "Channel must be a string."

    return not bool(errors), errors


def validate_event_data_row(row_data):
    """
    Validates a single row of event data.
    """
    errors = {}

    required_fields = ["customer_id", "event_type",
                       "event_source", "event_timestamp"]
    is_present, missing_errors = validate_required_fields(row_data, required_fields)
    if not is_present:
        errors.update(missing_errors)
        return False, errors

    if not is_valid_uuid(row_data.get("customer_id")):
        errors["customer_id"] = "Invalid customer_id. Must be a valid UUID."

    allowed_event_types = [
        "SMS_SENT", "SMS_DELIVERED", "SMS_CLICKED", "EKYC_ACHIEVED",
        "DISBURSEMENT", "LOAN_LOGIN", "BUREAU_CHECK", "OFFER_DETAILS",
        "BANK_DETAILS", "OTHER_DETAILS", "E_SIGN"
    ]
    if not is_valid_enum(row_data.get("event_type"), allowed_event_types):
        errors["event_type"] = (f"Invalid event_type. Must be one of "
                                f"{', '.join(allowed_event_types)}.")

    allowed_event_sources = ["Moengage", "LOS", "E-aggregator", "Insta"]
    if not is_valid_enum(row_data.get("event_source"), allowed_event_sources):
        errors["event_source"] = (f"Invalid event_source. Must be one of "
                                  f"{', '.join(allowed_event_sources)}.")

    if not is_valid_datetime(row_data.get("event_timestamp")):
        errors["event_timestamp"] = ("Invalid event_timestamp. "
                                     "Must be a valid ISO 8601 datetime string.")

    if "event_details" in row_data and \
            not isinstance(row_data["event_details"], dict):
        errors["event_details"] = "Event details must be a dictionary (JSON object)."

    return not bool(errors), errors


def validate_campaign_metric_data_row(row_data):
    """
    Validates a single row of campaign metric data.
    """
    errors = {}

    required_fields = ["campaign_unique_id", "campaign_name", "campaign_date",
                       "attempted_count", "sent_success_count",
                       "failed_count", "conversion_rate"]
    is_present, missing_errors = validate_required_fields(row_data, required_fields)
    if not is_present:
        errors.update(missing_errors)
        return False, errors

    if not isinstance(row_data.get("campaign_unique_id"), str) or \
            not row_data.get("campaign_unique_id").strip():
        errors["campaign_unique_id"] = ("Invalid or empty campaign_unique_id. "
                                        "Must be a non-empty string.")

    if not isinstance(row_data.get("campaign_name"), str) or \
            not row_data.get("campaign_name").strip():
        errors["campaign_name"] = ("Invalid or empty campaign_name. "
                                   "Must be a non-empty string.")

    if not is_valid_date(row_data.get("campaign_date")):
        errors["campaign_date"] = "Invalid campaign_date. Must be in YYYY-MM-DD format."

    if not isinstance(row_data.get("attempted_count"), int) or \
            row_data.get("attempted_count") < 0:
        errors["attempted_count"] = ("Attempted count must be a "
                                     "non-negative integer.")

    if not isinstance(row_data.get("sent_success_count"), int) or \
            row_data.get("sent_success_count") < 0:
        errors["sent_success_count"] = ("Sent success count must be a "
                                        "non-negative integer.")

    if not isinstance(row_data.get("failed_count"), int) or \
            row_data.get("failed_count") < 0:
        errors["failed_count"] = ("Failed count must be a "
                                  "non-negative integer.")

    if not isinstance(row_data.get("conversion_rate"), (int, float)) or \
            not (0 <= row_data.get("conversion_rate") <= 100):
        errors["conversion_rate"] = ("Conversion rate must be a number "
                                     "between 0 and 100.")

    return not bool(errors), errors