OFFER_SCHEMA = {
    "customer_id": {
        "required": True,
        "type": str,
        "regex": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    },
    "offer_type": {
        "required": True,
        "type": str,
        "allowed_values": ["Fresh", "Enrich", "New-old", "New-new"]
    },
    "offer_status": {
        "required": True,
        "type": str,
        "allowed_values": ["Active", "Inactive", "Expired"]
    },
    "propensity_flag": {
        "required": False,
        "type": str,
        "max_len": 50
    },
    "offer_start_date": {
        "required": True,
        "type": str,
        "regex": r"^\d{4}-\d{2}-\d{2}$"  # YYYY-MM-DD format
    },
    "offer_end_date": {
        "required": True,
        "type": str,
        "regex": r"^\d{4}-\d{2}-\d{2}$"  # YYYY-MM-DD format
    },
    "loan_application_number": {
        "required": False,
        "type": str,
        "max_len": 50
    },
    "attribution_channel": {
        "required": False,
        "type": str,
        "max_len": 50
    }
}