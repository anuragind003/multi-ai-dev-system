import re
from datetime import datetime, timezone
import dateutil.parser

class DataValidationService:
    """
    Service responsible for performing basic column-level data validation
    for incoming customer and offer data, as well as ingestion payloads.
    """

    def __init__(self):
        # Regular expressions for common data formats
        # Assuming 10-digit mobile numbers for India
        self.mobile_regex = r"^\d{10}$"
        # Standard PAN format: 5 letters, 4 digits, 1 letter
        self.pan_regex = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
        # Standard Aadhaar format: 12 digits
        self.aadhaar_regex = r"^\d{12}$"
        # Standard UUID format (case-insensitive)
        self.uuid_regex = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

        # Allowed values for enumerated fields as per BRD
        self.valid_offer_types = {'Fresh', 'Enrich', 'New-old', 'New-new'} # FR17
        self.valid_offer_statuses = {'Active', 'Inactive', 'Expired'} # FR16
        # FR21: C1 to C8 and other analytics-prescribed segments. Starting with C1-C8.
        # This set can be expanded based on "analytics-prescribed segments".
        self.valid_segments = {'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8'}
        # Based on integrations mentioned in BRD and system design
        self.valid_source_systems = {'Offermart', 'E-aggregator', 'MAS', 'LOS', 'Moengage'}

    def _validate_field(self, data: dict, field_name: str, required: bool = False,
                        data_type: type = None, regex: str = None, allowed_values: set = None) -> list[str]:
        """
        Helper method to validate a single field based on various criteria.
        Returns a list of error messages for the field.
        """
        errors = []
        value = data.get(field_name)

        if required and (value is None or (isinstance(value, str) and not value.strip())):
            errors.append(f"'{field_name}' is required.")
            return errors # If required and missing, no further validation for this field

        if value is not None:
            if data_type and not isinstance(value, data_type):
                errors.append(f"'{field_name}' must be of type {data_type.__name__}.")
            
            if isinstance(value, str) and regex and not re.fullmatch(regex, value):
                errors.append(f"'{field_name}' has an invalid format.")
            
            if allowed_values and value not in allowed_values:
                errors.append(f"'{field_name}' has an invalid value. Allowed values are: {', '.join(map(str, allowed_values))}.")
        
        return errors

    def validate_customer_data(self, customer_data: dict) -> tuple[bool, list[str]]:
        """
        Validates a dictionary representing customer data.
        Applies basic column-level validation as per FR2, NFR8.
        Ensures at least one primary identifier is present as per FR3.
        Returns (is_valid, errors_list).
        """
        errors = []

        # Validate primary identifiers (at least one required for deduplication FR3)
        mobile = customer_data.get('mobile_number')
        pan = customer_data.get('pan_number')
        aadhaar = customer_data.get('aadhaar_number')
        ucid = customer_data.get('ucid_number')
        
        if not any([mobile, pan, aadhaar, ucid]):
            errors.append("At least one primary identifier ('mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number') is required.")

        # Validate format of identifiers if present
        errors.extend(self._validate_field(customer_data, 'mobile_number', data_type=str, regex=self.mobile_regex))
        errors.extend(self._validate_field(customer_data, 'pan_number', data_type=str, regex=self.pan_regex))
        errors.extend(self._validate_field(customer_data, 'aadhaar_number', data_type=str, regex=self.aadhaar_regex))
        errors.extend(self._validate_field(customer_data, 'ucid_number', data_type=str)) # UCID format not specified, assume string

        # Other customer attributes
        errors.extend(self._validate_field(customer_data, 'customer_360_id', data_type=str))
        errors.extend(self._validate_field(customer_data, 'is_dnd', data_type=bool))
        errors.extend(self._validate_field(customer_data, 'segment', data_type=str, allowed_values=self.valid_segments))
        
        # 'attributes' is JSONB in DB, so it can be a dict in payload. Basic type check.
        if 'attributes' in customer_data and not isinstance(customer_data['attributes'], dict):
            errors.append("'attributes' must be a dictionary.")

        return not bool(errors), errors

    def validate_offer_data(self, offer_data: dict) -> tuple[bool, list[str]]:
        """
        Validates a dictionary representing offer data.
        Applies basic column-level validation as per FR2, NFR8.
        Returns (is_valid, errors_list).
        """
        errors = []

        # Required fields
        errors.extend(self._validate_field(offer_data, 'customer_id', required=True, data_type=str, regex=self.uuid_regex))
        errors.extend(self._validate_field(offer_data, 'source_offer_id', required=True, data_type=str))
        errors.extend(self._validate_field(offer_data, 'offer_type', required=True, data_type=str, allowed_values=self.valid_offer_types))
        errors.extend(self._validate_field(offer_data, 'offer_status', required=True, data_type=str, allowed_values=self.valid_offer_statuses))
        errors.extend(self._validate_field(offer_data, 'source_system', required=True, data_type=str, allowed_values=self.valid_source_systems))

        # Optional fields with specific types/values
        errors.extend(self._validate_field(offer_data, 'propensity', data_type=str))
        errors.extend(self._validate_field(offer_data, 'loan_application_number', data_type=str))
        errors.extend(self._validate_field(offer_data, 'channel', data_type=str))
        errors.extend(self._validate_field(offer_data, 'is_duplicate', data_type=bool))
        errors.extend(self._validate_field(offer_data, 'original_offer_id', data_type=str, regex=self.uuid_regex))

        # Date validation for 'valid_until'
        valid_until_str = offer_data.get('valid_until')
        offer_status = offer_data.get('offer_status')

        if offer_status == 'Active':
            if not valid_until_str:
                errors.append("'valid_until' is required for an 'Active' offer.")
            else:
                try:
                    valid_until_dt = dateutil.parser.parse(valid_until_str)
                    # Ensure it's a future date for active offers
                    if valid_until_dt <= datetime.now(timezone.utc):
                        errors.append("'valid_until' must be a future date for an 'Active' offer.")
                except ValueError:
                    errors.append("'valid_until' has an invalid date/time format.")
        elif valid_until_str: # If not active, but valid_until is provided, just check format
             try:
                dateutil.parser.parse(valid_until_str)
             except ValueError:
                errors.append("'valid_until' has an invalid date/time format.")

        return not bool(errors), errors

    def validate_e_aggregator_ingestion_payload(self, payload: dict) -> tuple[bool, list[str]]:
        """
        Validates the top-level payload structure for E-aggregator ingestion API.
        This validates the wrapper as per API endpoint definition.
        The actual customer/offer data inside 'payload' will be validated by
        `validate_customer_data` or `validate_offer_data` in the calling service/controller.
        (NFR9: The Lead Generation API shall validate data before pushing records to CDP.)
        """
        errors = []
        
        # Source system must specifically be 'E-aggregator' for this API
        errors.extend(self._validate_field(payload, 'source_system', required=True, data_type=str, allowed_values={'E-aggregator'}))
        # Data type for E-aggregator payload
        errors.extend(self._validate_field(payload, 'data_type', required=True, data_type=str, allowed_values={'lead', 'eligibility', 'status', 'offer'}))
        
        if 'payload' not in payload or not isinstance(payload['payload'], dict):
            errors.append("'payload' field is required and must be a dictionary.")
        
        return not bool(errors), errors