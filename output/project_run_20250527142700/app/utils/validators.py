import re
from datetime import datetime

class ValidationError(Exception):
    """Custom exception for data validation errors."""
    def __init__(self, message: str, errors: dict = None):
        super().__init__(message)
        self.errors = errors if errors is not None else {}

def validate_data(data: dict, schema: dict) -> dict:
    """
    Validates input data against a predefined schema.

    Args:
        data (dict): The input data to validate.
        schema (dict): A dictionary defining validation rules for each field.
                       Example schema rule for a field:
                       {
                           "required": True,
                           "type": str,
                           "min_len": 10,
                           "max_len": 10,
                           "regex": r"^\\d{10}$",
                           "allowed_values": ["value1", "value2"],
                           "default": "default_value"
                       }

    Returns:
        dict: The processed data with defaults applied and types coerced where possible.

    Raises:
        ValidationError: If any validation rule is violated.
    """
    all_errors = {}
    processed_data = data.copy()

    for field_name, rules in schema.items():
        field_errors = []
        value = processed_data.get(field_name)
        is_required = rules.get("required", False)
        expected_type = rules.get("type")

        # 1. Check for required fields
        if is_required and (value is None or (isinstance(value, str) and not value.strip())):
            field_errors.append(f"'{field_name}' is required.")
            all_errors[field_name] = field_errors
            continue # Skip further validation for this field if it's missing and required

        # If value is None but not required, and no default, skip further validation for this field
        if value is None and not is_required:
            if "default" in rules:
                processed_data[field_name] = rules["default"]
            continue

        # 2. Type validation and coercion
        if expected_type is not None:
            try:
                if expected_type == bool:
                    # Handle boolean coercion from string/int
                    if isinstance(value, str):
                        if value.lower() in ('true', '1', 'yes'):
                            processed_data[field_name] = True
                        elif value.lower() in ('false', '0', 'no'):
                            processed_data[field_name] = False
                        else:
                            raise ValueError
                    elif isinstance(value, int):
                        processed_data[field_name] = bool(value)
                    elif not isinstance(value, bool):
                        raise ValueError
                elif expected_type == datetime:
                    # Attempt to parse datetime strings
                    if isinstance(value, str):
                        processed_data[field_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    elif not isinstance(value, datetime):
                        raise ValueError
                else:
                    # For other types, attempt direct coercion
                    if not isinstance(value, expected_type):
                        processed_data[field_name] = expected_type(value)
            except (ValueError, TypeError):
                field_errors.append(f"'{field_name}' must be of type {expected_type.__name__}.")

        # Use the potentially coerced value for subsequent checks
        value = processed_data.get(field_name)

        # Only proceed with further validations if value is not None and no type errors yet
        if value is not None and not field_errors:
            # 3. String length validation
            if expected_type == str:
                min_len = rules.get("min_len")
                max_len = rules.get("max_len")
                if min_len is not None and len(value) < min_len:
                    field_errors.append(f"'{field_name}' must be at least {min_len} characters long.")
                if max_len is not None and len(value) > max_len:
                    field_errors.append(f"'{field_name}' must be at most {max_len} characters long.")

                # 4. Regex pattern validation
                regex = rules.get("regex")
                if regex is not None and not re.fullmatch(regex, value):
                    field_errors.append(f"'{field_name}' has an invalid format.")

            # 5. Allowed values validation
            allowed_values = rules.get("allowed_values")
            if allowed_values is not None and value not in allowed_values:
                field_errors.append(f"'{field_name}' has an invalid value. Allowed values are: {', '.join(map(str, allowed_values))}.")

        # Collect errors for this field
        if field_errors:
            all_errors[field_name] = field_errors

    # Raise exception if any errors were found
    if all_errors:
        raise ValidationError("Validation failed for one or more fields.", errors=all_errors)

    # 6. Apply defaults for missing non-required fields that weren't explicitly set
    for field_name, rules in schema.items():
        if field_name not in processed_data and "default" in rules:
            processed_data[field_name] = rules["default"]

    return processed_data

# --- Predefined Schemas for different data types based on BRD and System Design ---

CUSTOMER_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "pan": {"required": False, "type": str, "min_len": 10, "max_len": 10, "regex": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "aadhaar_ref_number": {"required": False, "type": str, "min_len": 12, "max_len": 12, "regex": r"^\d{12}$"},
    "ucid": {"required": False, "type": str},
    "previous_loan_app_number": {"required": False, "type": str},
    "customer_segment": {"required": False, "type": str, "allowed_values": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]}, # FR19
    "is_dnd": {"required": False, "type": bool, "default": False}, # FR21
    # Add other customer attributes as needed, e.g., name, address, etc.
    # For now, customer_attributes is JSONB in DB, so direct validation might be complex here.
    # "customer_attributes": {"required": False, "type": dict},
}

OFFER_SCHEMA = {
    "customer_id": {"required": True, "type": str}, # UUID as string
    "offer_type": {"required": False, "type": str, "allowed_values": ["Fresh", "Enrich", "New-old", "New-new"]}, # FR16
    "offer_status": {"required": False, "type": str, "allowed_values": ["Active", "Inactive", "Expired"], "default": "Active"}, # FR15
    "propensity_flag": {"required": False, "type": str}, # FR17
    "offer_start_date": {"required": False, "type": str}, # Date string, e.g., "YYYY-MM-DD"
    "offer_end_date": {"required": False, "type": str}, # Date string, e.g., "YYYY-MM-DD"
    "loan_application_number": {"required": False, "type": str},
    "attribution_channel": {"required": False, "type": str},
}

CUSTOMER_EVENT_SCHEMA = {
    "customer_id": {"required": True, "type": str}, # UUID as string
    "event_type": {"required": True, "type": str, "allowed_values": [
        "SMS_SENT", "SMS_DELIVERED", "SMS_CLICK", "CONVERSION",
        "APP_STAGE_LOGIN", "APP_STAGE_BUREAU_CHECK", "APP_STAGE_OFFER_DETAILS",
        "APP_STAGE_EKYC", "APP_STAGE_BANK_DETAILS", "APP_STAGE_OTHER_DETAILS",
        "APP_STAGE_ESIGN"
    ]}, # FR22
    "event_source": {"required": True, "type": str, "allowed_values": ["Moengage", "LOS"]}, # FR22
    "event_timestamp": {"required": False, "type": datetime, "default": datetime.now}, # Will be set by DB, but for API input, allow string
    "event_details": {"required": False, "type": dict}, # JSONB in DB, can be any dict
}

CAMPAIGN_SCHEMA = {
    "campaign_unique_identifier": {"required": True, "type": str},
    "campaign_name": {"required": True, "type": str},
    "campaign_date": {"required": True, "type": str}, # Date string, e.g., "YYYY-MM-DD"
    "targeted_customers_count": {"required": False, "type": int, "default": 0},
    "attempted_count": {"required": False, "type": int, "default": 0},
    "successfully_sent_count": {"required": False, "type": int, "default": 0},
    "failed_count": {"required": False, "type": int, "default": 0},
    "success_rate": {"required": False, "type": float, "default": 0.0},
    "conversion_rate": {"required": False, "type": float, "default": 0.0},
}

# --- API Input Schemas ---

LEAD_GENERATION_API_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "pan": {"required": False, "type": str, "min_len": 10, "max_len": 10, "regex": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "loan_type": {"required": True, "type": str},
    "source_channel": {"required": True, "type": str},
    "application_id": {"required": False, "type": str}, # Can be generated later if not provided
}

ELIGIBILITY_API_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "loan_application_number": {"required": True, "type": str},
    "eligibility_status": {"required": True, "type": str},
    "offer_id": {"required": False, "type": str}, # UUID as string
}

STATUS_API_SCHEMA = {
    "loan_application_number": {"required": True, "type": str},
    "application_stage": {"required": True, "type": str, "allowed_values": [
        "login", "bureau check", "offer details", "eKYC", "Bank details",
        "other details", "e-sign", "conversion", "rejected", "expired" # Added rejected/expired for completeness
    ]}, # FR22
    "status_details": {"required": False, "type": str},
    "event_timestamp": {"required": True, "type": str}, # Expecting ISO format string
}

ADMIN_UPLOAD_CUSTOMER_DETAILS_SCHEMA = {
    "file_type": {"required": True, "type": str, "allowed_values": ["Prospect", "TW Loyalty", "Topup", "Employee loans"]}, # FR29
    "file_content_base64": {"required": True, "type": str}, # Base64 encoded file content
    "uploaded_by": {"required": True, "type": str},
}