import re

# --- Predefined Schemas for different data types based on BRD and System Design ---

# Schema for Customer data (used in file uploads and potentially APIs)
# Derived from app/routes/admin.py EXPECTED_COLUMNS and database schema
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

# Schema for Lead Generation API input (FR9)
LEAD_GENERATION_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "pan": {"required": False, "type": str, "min_len": 10, "max_len": 10, "regex": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "loan_type": {"required": True, "type": str, "allowed_values": ["Prospect", "TW Loyalty", "Topup", "Employee loans", "Loyalty", "Preapproved", "E-aggregator"]}, # Based on FR3, FR29
    "source_channel": {"required": True, "type": str}, # e.g., 'Insta', 'E-aggregator', 'Offermart'
    "application_id": {"required": False, "type": str}, # External application ID
}

# Schema for Eligibility API input (FR9)
ELIGIBILITY_SCHEMA = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "loan_application_number": {"required": True, "type": str},
    "eligibility_status": {"required": True, "type": str, "allowed_values": ["Eligible", "Not Eligible", "Pending", "Approved", "Rejected"]}, # Example values
    "offer_id": {"required": False, "type": str, "regex": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"}, # UUID format
}

# Schema for Status API input (FR9)
STATUS_UPDATE_SCHEMA = {
    "loan_application_number": {"required": True, "type": str},
    "application_stage": {"required": True, "type": str, "allowed_values": [ # FR22
        "login", "bureau check", "offer details", "eKYC", "Bank details", "other details", "e-sign",
        "SMS sent", "SMS delivered", "SMS click", "conversion" # Moengage/LOS events
    ]},
    "status_details": {"required": False, "type": str},
    "event_timestamp": {"required": True, "type": str, "regex": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$"}, # ISO 8601 format
}

# Schema for Offer data (if offers are directly ingested/updated via API, e.g., from Offermart)
# Based on 'offers' table schema and FR15, FR16, FR17
OFFER_SCHEMA = {
    "customer_id": {"required": True, "type": str, "regex": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"}, # UUID format
    "offer_type": {"required": True, "type": str, "allowed_values": ["Fresh", "Enrich", "New-old", "New-new"]}, # FR16
    "offer_status": {"required": True, "type": str, "allowed_values": ["Active", "Inactive", "Expired"]}, # FR15
    "propensity_flag": {"required": False, "type": str}, # FR17, e.g., 'dominant tradeline'
    "offer_start_date": {"required": True, "type": str, "regex": r"^\d{4}-\d{2}-\d{2}$"}, # YYYY-MM-DD
    "offer_end_date": {"required": True, "type": str, "regex": r"^\d{4}-\d{2}-\d{2}$"}, # YYYY-MM-DD
    "loan_application_number": {"required": False, "type": str},
    "attribution_channel": {"required": False, "type": str},
}

# Schema for Customer Event data (if events are directly ingested, beyond status updates)
# Based on 'customer_events' table schema and FR21, FR22
CUSTOMER_EVENT_SCHEMA = {
    "customer_id": {"required": True, "type": str, "regex": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"}, # UUID format
    "event_type": {"required": True, "type": str, "allowed_values": [ # FR22
        "SMS_SENT", "SMS_DELIVERED", "SMS_CLICK", "CONVERSION",
        "APP_STAGE_LOGIN", "APP_STAGE_BUREAU_CHECK", "APP_STAGE_OFFER_DETAILS",
        "APP_STAGE_EKYC", "APP_STAGE_BANK_DETAILS", "APP_STAGE_OTHER_DETAILS", "APP_STAGE_E_SIGN"
    ]},
    "event_source": {"required": True, "type": str, "allowed_values": ["Moengage", "LOS", "CDP_INTERNAL"]}, # FR21, FR22
    "event_timestamp": {"required": True, "type": str, "regex": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$"}, # ISO 8601 format
    "event_details": {"required": False, "type": dict}, # JSONB type, validate as dict
}