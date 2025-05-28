import re
from datetime import datetime

class ValidationError(Exception):
    """Custom exception for schema validation errors."""
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors if errors is not None else {}

def validate_data(data: dict, schema: dict) -> dict:
    """
    Validates input data against a predefined schema.

    Args:
        data (dict): The input data to validate.
        schema (dict): The schema definition. Each key is a field name,
                       and its value is a dictionary of rules (e.g., 'type', 'required', 'default', 'enum', 'max_length', 'pattern', 'format').

    Returns:
        dict: The validated and processed data with defaults applied.

    Raises:
        ValidationError: If validation fails.
    """
    processed_data = data.copy()
    all_errors = {}

    for field_name, rules in schema.items():
        value = processed_data.get(field_name)

        # 1. Check for required fields
        # A field is considered missing if its value is None or an empty string after stripping whitespace
        if rules.get("required") and (value is None or (isinstance(value, str) and not value.strip())):
            all_errors.setdefault(field_name, []).append(f"{field_name} is required and cannot be empty.")
            continue # Skip further validation for this field if it's missing/empty and required

        # If field is not required and not present/empty, apply default or skip further validation
        if value is None or (isinstance(value, str) and not value.strip()):
            if "default" in rules:
                processed_data[field_name] = rules["default"]
            continue

        # 2. Type validation
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            all_errors.setdefault(field_name, []).append(f"{field_name} must be of type {expected_type.__name__}.")
            continue # Skip further validation for this field if type is wrong

        # 3. Enum validation
        enum_values = rules.get("enum")
        if enum_values and value not in enum_values:
            all_errors.setdefault(field_name, []).append(f"{field_name} must be one of {', '.join(map(str, enum_values))}.")

        # 4. Max length validation for strings
        max_length = rules.get("max_length")
        if max_length and isinstance(value, str) and len(value) > max_length:
            all_errors.setdefault(field_name, []).append(f"{field_name} exceeds maximum length of {max_length}.")

        # 5. Pattern validation for strings (e.g., mobile number, PAN, Aadhaar)
        pattern = rules.get("pattern")
        if pattern and isinstance(value, str):
            if not re.fullmatch(pattern, value):
                all_errors.setdefault(field_name, []).append(f"{field_name} does not match the required format.")

        # 6. Specific format validation (e.g., datetime string, date string)
        data_format = rules.get("format")
        if data_format and isinstance(value, str):
            if data_format == "datetime":
                try:
                    # Attempt to parse common ISO 8601 formats, including with 'Z' for UTC
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    all_errors.setdefault(field_name, []).append(f"{field_name} must be a valid ISO 8601 datetime string (e.g., YYYY-MM-DDTHH:MM:SSZ).")
            elif data_format == "date":
                try:
                    datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    all_errors.setdefault(field_name, []).append(f"{field_name} must be a valid date string in YYYY-MM-DD format.")

    if all_errors:
        raise ValidationError("Validation failed for one or more fields.", errors=all_errors)

    return processed_data

# --- Predefined Schemas for different data types based on BRD and System Design ---

# Schema for /api/leads (Lead Generation API)
LEAD_GENERATION_SCHEMA = {
    "mobile_number": {"type": str, "required": True, "max_length": 20, "pattern": r"^\d{10}$"},
    "pan": {"type": str, "required": True, "max_length": 10, "pattern": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "loan_type": {"type": str, "required": True},
    "source_channel": {"type": str, "required": True},
    "application_id": {"type": str, "required": True}
}

# Schema for /api/eligibility (Eligibility API)
ELIGIBILITY_SCHEMA = {
    "mobile_number": {"type": str, "required": True, "max_length": 20, "pattern": r"^\d{10}$"},
    "loan_application_number": {"type": str, "required": True, "max_length": 50},
    "eligibility_status": {"type": str, "required": True},
    "offer_id": {"type": str, "required": True} # Assuming UUID string, but not validating format here
}

# Schema for /api/status (Status API)
STATUS_UPDATE_SCHEMA = {
    "loan_application_number": {"type": str, "required": True, "max_length": 50},
    "application_stage": {"type": str, "required": True},
    "status_details": {"type": str, "required": True},
    "event_timestamp": {"type": str, "required": True, "format": "datetime"}
}

# Schema for /api/admin/upload/customer-details (Admin File Upload)
ADMIN_UPLOAD_SCHEMA = {
    "file_type": {
        "type": str,
        "required": True,
        "enum": ["Prospect", "TW Loyalty", "Topup", "Employee loans"]
    },
    "file_content_base64": {"type": str, "required": True},
    "uploaded_by": {"type": str, "required": True}
}

# Schema for daily data ingestion from Offermart (FR7) - Customer Data
OFFERMART_CUSTOMER_DATA_SCHEMA = {
    "mobile_number": {"type": str, "required": True, "max_length": 20, "pattern": r"^\d{10}$"},
    "pan": {"type": str, "required": False, "max_length": 10, "pattern": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "aadhaar_ref_number": {"type": str, "required": False, "max_length": 12, "pattern": r"^\d{12}$"},
    "ucid": {"type": str, "required": False, "max_length": 50},
    "previous_loan_app_number": {"type": str, "required": False, "max_length": 50},
    "customer_segment": {"type": str, "required": False, "max_length": 10}, # e.g., C1 to C8
    "is_dnd": {"type": bool, "required": False, "default": False},
    "customer_attributes": {"type": dict, "required": False, "default": {}} # For flexible attributes
}

# Schema for daily data ingestion from Offermart (FR7) - Offer Data
OFFERMART_OFFER_DATA_SCHEMA = {
    "mobile_number": {"type": str, "required": True, "max_length": 20, "pattern": r"^\d{10}$"}, # To link to customer
    "offer_type": {"type": str, "required": True, "enum": ["Fresh", "Enrich", "New-old", "New-new"]},
    "offer_status": {"type": str, "required": True, "enum": ["Active", "Inactive", "Expired"]},
    "propensity_flag": {"type": str, "required": False, "max_length": 50},
    "offer_start_date": {"type": str, "required": True, "format": "date"}, # YYYY-MM-DD
    "offer_end_date": {"type": str, "required": True, "format": "date"}, # YYYY-MM-DD
    "loan_application_number": {"type": str, "required": False, "max_length": 50},
    "attribution_channel": {"type": str, "required": False, "max_length": 50}
}