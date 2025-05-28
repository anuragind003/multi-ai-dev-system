import re
import uuid
from datetime import datetime

class ValidationService:
    """
    Service class for performing various data validations.
    This includes basic column-level data validation for incoming data
    from different sources like Offermart, E-aggregators, Moengage, and LOS.
    """

    # Regex patterns for common Indian identifiers
    MOBILE_NUMBER_PATTERN = re.compile(r"^[6-9]\d{9}$")
    PAN_NUMBER_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
    AADHAAR_NUMBER_PATTERN = re.compile(r"^\d{4}\s\d{4}\s\d{4}$|^\d{12}$") # Allows with or without spaces

    # Allowed values for enums/flags
    ALLOWED_OFFER_TYPES = ['Fresh', 'Enrich', 'New-old', 'New-new']
    ALLOWED_OFFER_STATUSES = ['Active', 'Inactive', 'Expired']
    ALLOWED_SOURCE_SYSTEMS = ['Offermart', 'E-aggregator', 'Moengage', 'LOS', 'MAS']
    ALLOWED_EVENT_TYPES = [
        'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICK',
        'EKYC_ACHIEVED', 'DISBURSEMENT',
        'JOURNEY_LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS',
        'BANK_DETAILS', 'OTHER_DETAILS', 'E_SIGN'
    ]

    @staticmethod
    def _is_valid_uuid(val: str) -> bool:
        """Checks if a string is a valid UUID."""
        try:
            uuid.UUID(val)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_mobile_number(val: str) -> bool:
        """Checks if a string is a valid Indian mobile number format."""
        return bool(ValidationService.MOBILE_NUMBER_PATTERN.match(val))

    @staticmethod
    def _is_valid_pan_number(val: str) -> bool:
        """Checks if a string is a valid Indian PAN number format."""
        return bool(ValidationService.PAN_NUMBER_PATTERN.match(val))

    @staticmethod
    def _is_valid_aadhaar_number(val: str) -> bool:
        """Checks if a string is a valid Indian Aadhaar number format."""
        return bool(ValidationService.AADHAAR_NUMBER_PATTERN.match(val))

    @staticmethod
    def _is_valid_timestamp(val: str) -> bool:
        """Checks if a string is a valid ISO 8601 timestamp."""
        try:
            datetime.fromisoformat(val.replace('Z', '+00:00')) # Handle 'Z' for UTC
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_boolean(val) -> bool:
        """Checks if a value is a boolean."""
        return isinstance(val, bool)

    @staticmethod
    def validate_customer_data(data: dict) -> tuple[bool, dict]:
        """
        Validates incoming customer data.
        Ensures at least one primary identifier is present and correctly formatted.
        """
        errors = {}

        # At least one identifier must be present
        identifiers = ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number']
        if not any(data.get(id_key) for id_key in identifiers):
            errors['identifiers'] = "At least one of mobile_number, pan_number, aadhaar_number, or ucid_number is required."

        # Validate format of provided identifiers
        if 'mobile_number' in data and data['mobile_number'] is not None:
            if not isinstance(data['mobile_number'], str) or not ValidationService._is_valid_mobile_number(data['mobile_number']):
                errors['mobile_number'] = "Invalid mobile number format."
        if 'pan_number' in data and data['pan_number'] is not None:
            if not isinstance(data['pan_number'], str) or not ValidationService._is_valid_pan_number(data['pan_number']):
                errors['pan_number'] = "Invalid PAN number format."
        if 'aadhaar_number' in data and data['aadhaar_number'] is not None:
            if not isinstance(data['aadhaar_number'], str) or not ValidationService._is_valid_aadhaar_number(data['aadhaar_number']):
                errors['aadhaar_number'] = "Invalid Aadhaar number format."
        if 'ucid_number' in data and data['ucid_number'] is not None:
            if not isinstance(data['ucid_number'], str) or not data['ucid_number'].strip():
                errors['ucid_number'] = "UCID number must be a non-empty string."

        # Validate is_dnd
        if 'is_dnd' in data and data['is_dnd'] is not None:
            if not ValidationService._is_valid_boolean(data['is_dnd']):
                errors['is_dnd'] = "is_dnd must be a boolean."

        # Validate segment (optional, but if present, must be string)
        if 'segment' in data and data['segment'] is not None:
            if not isinstance(data['segment'], str) or not data['segment'].strip():
                errors['segment'] = "Segment must be a non-empty string."

        # Validate attributes (optional, but if present, must be dict)
        if 'attributes' in data and data['attributes'] is not None:
            if not isinstance(data['attributes'], dict):
                errors['attributes'] = "Attributes must be a dictionary (JSONB)."

        return not bool(errors), errors

    @staticmethod
    def validate_offer_data(data: dict) -> tuple[bool, dict]:
        """
        Validates incoming offer data.
        """
        errors = {}
        required_fields = ['customer_id', 'source_offer_id', 'offer_type', 'offer_status', 'valid_until', 'source_system']

        for field in required_fields:
            if field not in data or data[field] is None:
                errors[field] = f"'{field}' is required."

        if 'customer_id' in data and data['customer_id'] is not None:
            if not isinstance(data['customer_id'], str) or not ValidationService._is_valid_uuid(data['customer_id']):
                errors['customer_id'] = "Invalid customer_id format (must be a valid UUID string)."

        if 'source_offer_id' in data and data['source_offer_id'] is not None:
            if not isinstance(data['source_offer_id'], str) or not data['source_offer_id'].strip():
                errors['source_offer_id'] = "Source offer ID must be a non-empty string."

        if 'offer_type' in data and data['offer_type'] is not None:
            if data['offer_type'] not in ValidationService.ALLOWED_OFFER_TYPES:
                errors['offer_type'] = f"Invalid offer_type. Must be one of {ValidationService.ALLOWED_OFFER_TYPES}."

        if 'offer_status' in data and data['offer_status'] is not None:
            if data['offer_status'] not in ValidationService.ALLOWED_OFFER_STATUSES:
                errors['offer_status'] = f"Invalid offer_status. Must be one of {ValidationService.ALLOWED_OFFER_STATUSES}."

        if 'valid_until' in data and data['valid_until'] is not None:
            if not isinstance(data['valid_until'], str) or not ValidationService._is_valid_timestamp(data['valid_until']):
                errors['valid_until'] = "Invalid valid_until format. Must be a valid ISO 8601 timestamp string."

        if 'source_system' in data and data['source_system'] is not None:
            if data['source_system'] not in ValidationService.ALLOWED_SOURCE_SYSTEMS:
                errors['source_system'] = f"Invalid source_system. Must be one of {ValidationService.ALLOWED_SOURCE_SYSTEMS}."

        if 'propensity' in data and data['propensity'] is not None:
            if not isinstance(data['propensity'], str) or not data['propensity'].strip():
                errors['propensity'] = "Propensity must be a non-empty string."

        if 'loan_application_number' in data and data['loan_application_number'] is not None:
            if not isinstance(data['loan_application_number'], str) or not data['loan_application_number'].strip():
                errors['loan_application_number'] = "Loan application number must be a non-empty string."

        if 'channel' in data and data['channel'] is not None:
            if not isinstance(data['channel'], str) or not data['channel'].strip():
                errors['channel'] = "Channel must be a non-empty string."

        if 'is_duplicate' in data and data['is_duplicate'] is not None:
            if not ValidationService._is_valid_boolean(data['is_duplicate']):
                errors['is_duplicate'] = "is_duplicate must be a boolean."

        if 'original_offer_id' in data and data['original_offer_id'] is not None:
            if not isinstance(data['original_offer_id'], str) or not ValidationService._is_valid_uuid(data['original_offer_id']):
                errors['original_offer_id'] = "Invalid original_offer_id format (must be a valid UUID string)."

        return not bool(errors), errors

    @staticmethod
    def validate_e_aggregator_payload(payload: dict) -> tuple[bool, dict]:
        """
        Validates the payload structure for E-aggregator data ingestion.
        Delegates to specific data validation based on 'data_type'.
        """
        errors = {}
        required_fields = ['source_system', 'data_type', 'payload']

        for field in required_fields:
            if field not in payload or payload[field] is None:
                errors[field] = f"'{field}' is required."

        if errors:
            return False, errors

        if payload['source_system'] not in ValidationService.ALLOWED_SOURCE_SYSTEMS:
            errors['source_system'] = f"Invalid source_system. Must be one of {ValidationService.ALLOWED_SOURCE_SYSTEMS}."
        elif payload['source_system'] != 'E-aggregator':
            errors['source_system'] = "Source system for this endpoint must be 'E-aggregator'."

        if not isinstance(payload['payload'], dict):
            errors['payload'] = "Inner 'payload' must be a dictionary."

        if errors:
            return False, errors

        # Delegate to specific validation based on data_type
        data_type = payload.get('data_type')
        inner_data = payload.get('payload', {})

        if data_type == 'customer_offer': # Assuming E-aggregator sends combined customer and offer data
            is_customer_valid, customer_errors = ValidationService.validate_customer_data(inner_data)
            is_offer_valid, offer_errors = ValidationService.validate_offer_data(inner_data) # Assuming offer data is part of the same payload
            if not is_customer_valid:
                errors['customer_data'] = customer_errors
            if not is_offer_valid:
                errors['offer_data'] = offer_errors
        elif data_type == 'lead_generation':
            # Specific validation for lead generation data (e.g., mobile, name, etc.)
            # For now, let's assume it's a subset of customer data
            is_valid, lead_errors = ValidationService.validate_customer_data(inner_data)
            if not is_valid:
                errors['lead_data'] = lead_errors
        elif data_type == 'eligibility' or data_type == 'status_update':
            # Specific validation for eligibility/status updates
            # These might require customer_id and specific status fields
            if 'customer_id' not in inner_data or not ValidationService._is_valid_uuid(inner_data['customer_id']):
                errors['customer_id'] = "customer_id (UUID) is required for eligibility/status updates."
            if 'offer_id' in inner_data and not ValidationService._is_valid_uuid(inner_data['offer_id']):
                errors['offer_id'] = "offer_id (UUID) must be valid if provided."
            # Add more specific checks for eligibility/status fields as needed
        else:
            errors['data_type'] = f"Unsupported data_type: '{data_type}'."

        return not bool(errors), errors

    @staticmethod
    def validate_moengage_event(data: dict) -> tuple[bool, dict]:
        """
        Validates incoming Moengage event data.
        """
        errors = {}
        required_fields = ['customer_mobile', 'event_type', 'timestamp', 'campaign_id']

        for field in required_fields:
            if field not in data or data[field] is None:
                errors[field] = f"'{field}' is required."

        if errors:
            return False, errors

        if not isinstance(data['customer_mobile'], str) or not ValidationService._is_valid_mobile_number(data['customer_mobile']):
            errors['customer_mobile'] = "Invalid customer_mobile format."

        if data['event_type'] not in ValidationService.ALLOWED_EVENT_TYPES:
            errors['event_type'] = f"Invalid event_type. Must be one of {ValidationService.ALLOWED_EVENT_TYPES}."
        elif not data['event_type'].startswith('SMS_'):
            errors['event_type'] = "Moengage event_type must start with 'SMS_'."

        if not isinstance(data['timestamp'], str) or not ValidationService._is_valid_timestamp(data['timestamp']):
            errors['timestamp'] = "Invalid timestamp format. Must be a valid ISO 8601 timestamp string."

        if not isinstance(data['campaign_id'], str) or not data['campaign_id'].strip():
            errors['campaign_id'] = "Campaign ID must be a non-empty string."

        if 'details' in data and data['details'] is not None:
            if not isinstance(data['details'], dict):
                errors['details'] = "Details must be a dictionary (JSONB)."

        return not bool(errors), errors

    @staticmethod
    def validate_los_event(data: dict) -> tuple[bool, dict]:
        """
        Validates incoming LOS event data.
        """
        errors = {}
        required_fields = ['loan_application_number', 'event_type', 'timestamp', 'customer_id']

        for field in required_fields:
            if field not in data or data[field] is None:
                errors[field] = f"'{field}' is required."

        if errors:
            return False, errors

        if not isinstance(data['loan_application_number'], str) or not data['loan_application_number'].strip():
            errors['loan_application_number'] = "Loan application number must be a non-empty string."

        if data['event_type'] not in ValidationService.ALLOWED_EVENT_TYPES:
            errors['event_type'] = f"Invalid event_type. Must be one of {ValidationService.ALLOWED_EVENT_TYPES}."
        elif not (data['event_type'].startswith('EKYC_') or data['event_type'].startswith('DISBURSEMENT') or data['event_type'].startswith('JOURNEY_')):
            errors['event_type'] = "LOS event_type must be related to EKYC, Disbursement, or Journey stages."

        if not isinstance(data['timestamp'], str) or not ValidationService._is_valid_timestamp(data['timestamp']):
            errors['timestamp'] = "Invalid timestamp format. Must be a valid ISO 8601 timestamp string."

        if not isinstance(data['customer_id'], str) or not ValidationService._is_valid_uuid(data['customer_id']):
            errors['customer_id'] = "Invalid customer_id format (must be a valid UUID string)."

        if 'details' in data and data['details'] is not None:
            if not isinstance(data['details'], dict):
                errors['details'] = "Details must be a dictionary (JSONB)."

        return not bool(errors), errors

    @staticmethod
    def validate_offermart_data_batch(data_list: list[dict]) -> tuple[bool, list[dict]]:
        """
        Validates a batch of data records from Offermart.
        Each record is expected to contain both customer and offer-related fields.
        Returns overall validity and a list of errors for each record.
        """
        all_valid = True
        batch_errors = []

        for i, record in enumerate(data_list):
            record_errors = {}
            # Offermart data is likely a flat structure containing both customer and offer details
            # We can reuse existing validators by passing relevant parts of the record
            is_customer_valid, customer_errors = ValidationService.validate_customer_data(record)
            if not is_customer_valid:
                record_errors.update(customer_errors)

            is_offer_valid, offer_errors = ValidationService.validate_offer_data(record)
            if not is_offer_valid:
                record_errors.update(offer_errors)

            if record_errors:
                all_valid = False
                batch_errors.append({'record_index': i, 'errors': record_errors, 'data': record})

        return all_valid, batch_errors