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
        schema (dict): The schema definition.

    Returns:
        dict: The validated and processed data with defaults applied.

    Raises:
        ValidationError: If validation fails for any field.
    """
    processed_data = data.copy()
    all_errors = {}

    for field_name, rules in schema.items():
        is_required = rules.get("required", False)
        field_type = rules.get("type")
        allowed_values = rules.get("allowed_values")
        min_len = rules.get("min_len")
        max_len = rules.get("max_len")
        regex_pattern = rules.get("regex")
        default_value = rules.get("default")

        value = processed_data.get(field_name)

        if value is None or (isinstance(value, str) and not value.strip()): # Treat empty string as None for validation
            if is_required:
                all_errors.setdefault(field_name, []).append(f"{field_name} is required.")
            elif default_value is not None:
                processed_data[field_name] = default_value
            continue # Skip further validation for missing/empty non-required fields

        # Type validation
        if field_type:
            if isinstance(field_type, tuple): # Handle multiple allowed types (e.g., (int, float))
                if not isinstance(value, field_type):
                    all_errors.setdefault(field_name, []).append(f"{field_name} must be of type {', '.join([t.__name__ for t in field_type])}.")
                    continue
            elif not isinstance(value, field_type):
                # Special handling for boolean conversion from string
                if field_type is bool and isinstance(value, str):
                    if value.lower() in ['true', '1']:
                        processed_data[field_name] = True
                    elif value.lower() in ['false', '0']:
                        processed_data[field_name] = False
                    else:
                        all_errors.setdefault(field_name, []).append(f"{field_name} must be a boolean (true/false or 1/0).")
                        continue
                else:
                    all_errors.setdefault(field_name, []).append(f"{field_name} must be of type {field_type.__name__}.")
                    continue

        # String-specific validations
        if isinstance(value, str):
            if min_len is not None and len(value) < min_len:
                all_errors.setdefault(field_name, []).append(f"{field_name} must be at least {min_len} characters long.")
            if max_len is not None and len(value) > max_len:
                all_errors.setdefault(field_name, []).append(f"{field_name} must be at most {max_len} characters long.")
            if regex_pattern:
                if not re.match(regex_pattern, value):
                    all_errors.setdefault(field_name, []).append(f"{field_name} format is invalid.")
        
        # Allowed values validation
        if allowed_values and value not in allowed_values:
            all_errors.setdefault(field_name, []).append(f"{field_name} must be one of {', '.join(map(str, allowed_values))}.")

    if all_errors:
        raise ValidationError("Validation failed for one or more fields.", errors=all_errors)

    return processed_data

# --- Predefined Schemas for different data types based on BRD and System Design ---

# Schema for Customer data (used in file uploads and potentially APIs)
CUSTOMER_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "pan": {"required": False, "type": str, "min_len": 10, "max_len": 10, "regex": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "aadhaar_ref_number": {"required": False, "type": str, "min_len": 12, "max_len": 12, "regex": r"^\d{12}$"},
    "ucid": {"required": False, "type": str},
    "previous_loan_app_number": {"required": False, "type": str},
    "customer_segment": {"required": False, "type": str, "allowed_values": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]}, # FR19
    "is_dnd": {"required": False, "type": bool, "default": False}, # FR21
    "customer_attributes": {"required": False, "type": dict}, # JSONB type, validate as dict
}

# Schema for /api/leads (POST)
LEAD_GENERATION_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "pan": {"required": False, "type": str, "min_len": 10, "max_len": 10, "regex": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "loan_type": {"required": True, "type": str},
    "source_channel": {"required": True, "type": str},
    "application_id": {"required": False, "type": str},
}

# Schema for /api/eligibility (POST)
ELIGIBILITY_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "loan_application_number": {"required": True, "type": str},
    "eligibility_status": {"required": True, "type": str},
    "offer_id": {"required": False, "type": str}, # UUID string
}

# Schema for /api/status (POST)
STATUS_UPDATE_SCHEMA = {
    "loan_application_number": {"required": True, "type": str},
    "application_stage": {"required": True, "type": str},
    "status_details": {"required": False, "type": str},
    "event_timestamp": {"required": True, "type": str}, # Will need datetime parsing in actual logic
}

# Schema for /api/admin/upload/customer-details (POST)
ADMIN_UPLOAD_SCHEMA = {
    "file_type": {"required": True, "type": str, "allowed_values": ["Prospect", "TW Loyalty", "Topup", "Employee loans"]},
    "file_content_base64": {"required": True, "type": str},
    "uploaded_by": {"required": True, "type": str},
}

# Schema for Offer data (used internally or for updates)
OFFER_SCHEMA = {
    "customer_id": {"required": True, "type": str}, # UUID string
    "offer_type": {"required": True, "type": str, "allowed_values": ["Fresh", "Enrich", "New-old", "New-new"]}, # FR16
    "offer_status": {"required": True, "type": str, "allowed_values": ["Active", "Inactive", "Expired"]}, # FR15
    "propensity_flag": {"required": False, "type": str}, # FR17
    "offer_start_date": {"required": False, "type": str}, # Date string, will need parsing
    "offer_end_date": {"required": False, "type": str}, # Date string, will need parsing
    "loan_application_number": {"required": False, "type": str},
    "attribution_channel": {"required": False, "type": str},
}

# Schema for Customer Event data (used internally or for updates)
CUSTOMER_EVENT_SCHEMA = {
    "customer_id": {"required": True, "type": str}, # UUID string
    "event_type": {"required": True, "type": str, "allowed_values": [
        "SMS_SENT", "SMS_DELIVERED", "SMS_CLICK", "CONVERSION",
        "APP_STAGE_LOGIN", "APP_STAGE_BUREAU_CHECK", "APP_STAGE_OFFER_DETAILS",
        "APP_STAGE_EKYC", "APP_STAGE_BANK_DETAILS", "APP_STAGE_OTHER_DETAILS",
        "APP_STAGE_ESIGN"
    ]}, # FR22
    "event_source": {"required": True, "type": str, "allowed_values": ["Moengage", "LOS"]}, # FR22
    "event_timestamp": {"required": True, "type": str}, # Will need datetime parsing
    "event_details": {"required": False, "type": dict}, # JSONB type
}

# Schema for Campaign data
CAMPAIGN_SCHEMA = {
    "campaign_unique_identifier": {"required": True, "type": str},
    "campaign_name": {"required": True, "type": str},
    "campaign_date": {"required": True, "type": str}, # Date string
    "targeted_customers_count": {"required": False, "type": int, "default": 0},
    "attempted_count": {"required": False, "type": int, "default": 0},
    "successfully_sent_count": {"required": False, "type": int, "default": 0},
    "failed_count": {"required": False, "type": int, "default": 0},
    "success_rate": {"required": False, "type": (int, float), "default": 0.0}, # Numeric(5,2)
    "conversion_rate": {"required": False, "type": (int, float), "default": 0.0}, # Numeric(5,2)
}

# Schema for Data Ingestion Log (for internal use, but good to define)
DATA_INGESTION_LOG_SCHEMA = {
    "file_name": {"required": True, "type": str},
    "upload_timestamp": {"required": True, "type": str}, # Datetime string
    "status": {"required": True, "type": str, "allowed_values": ["SUCCESS", "FAILED", "PARTIAL"]},
    "error_details": {"required": False, "type": str},
    "uploaded_by": {"required": True, "type": str},
}