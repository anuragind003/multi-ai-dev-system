import re
from datetime import datetime
import uuid
import json


class ValidationService:
    """
    A service class for performing basic column-level data validations.
    This service is responsible for ensuring data quality at the point of
    ingestion, whether from real-time APIs or batch file uploads.
    """

    # Regex patterns for common identifiers
    PAN_REGEX = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    AADHAAR_REGEX = r"^\d{12}$"
    MOBILE_NUMBER_REGEX = r"^\d{10}$"  # Assuming 10-digit Indian mobile numbers

    # Allowed values for enum-like fields
    ALLOWED_OFFER_TYPES = {'Fresh', 'Enrich', 'New-old', 'New-new'}
    ALLOWED_OFFER_STATUSES = {'Active', 'Inactive', 'Expired'}
    # FR20: customer segments (C1 to C8 and other analytics-prescribed segments)
    # Added 'Default' and 'Other' for flexibility in initial data.
    ALLOWED_CUSTOMER_SEGMENTS = {
        'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'Default', 'Other'
    }
    ALLOWED_EVENT_TYPES = {
        'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICKED', 'EKYC_ACHIEVED',
        'DISBURSEMENT', 'LOAN_LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS',
        'BANK_DETAILS', 'OTHER_DETAILS', 'E_SIGN'
    }
    ALLOWED_EVENT_SOURCES = {'Moengage', 'LOS', 'E-aggregator'}
    ALLOWED_INGESTION_STATUSES = {'SUCCESS', 'FAILED', 'PROCESSING'}

    def __init__(self):
        pass

    def _validate_required_fields(self, data: dict, required_fields: list) -> dict:
        """
        Checks if all required fields are present in the data and are not empty.
        """
        errors = {}
        for field in required_fields:
            if field not in data or data[field] is None or \
               (isinstance(data[field], str) and not data[field].strip()):
                errors[field] = f"'{field}' is a required field."
        return errors

    def _validate_string_field(self, data: dict, field_name: str,
                               max_length: int = None) -> dict:
        """
        Validates if a field is a non-empty string and optionally checks max
        length.
        """
        errors = {}
        value = data.get(field_name)
        if value is not None:
            if not isinstance(value, str):
                errors[field_name] = f"'{field_name}' must be a string."
            elif not value.strip():
                errors[field_name] = f"'{field_name}' cannot be empty."
            elif max_length and len(value) > max_length:
                errors[field_name] = f"'{field_name}' exceeds maximum length " \
                                     f"of {max_length} characters."
        return errors

    def _validate_boolean_field(self, data: dict, field_name: str) -> dict:
        """
        Validates if a field is a boolean. Attempts to convert common string
        representations.
        """
        errors = {}
        value = data.get(field_name)
        if value is not None:
            if isinstance(value, str):
                lower_value = value.lower()
                if lower_value in ['true', '1', 'yes']:
                    data[field_name] = True
                elif lower_value in ['false', '0', 'no']:
                    data[field_name] = False
                else:
                    errors[field_name] = f"'{field_name}' must be a boolean " \
                                         f"value (True/False, 1/0, yes/no)."
            elif not isinstance(value, bool):
                errors[field_name] = f"'{field_name}' must be a boolean value."
        return errors

    def _validate_numeric_field(self, data: dict, field_name: str,
                                value_type: type = int, min_val=None,
                                max_val=None) -> dict:
        """
        Validates if a field is numeric and optionally within a range.
        Updates the data dictionary with the converted numeric type.
        """
        errors = {}
        value = data.get(field_name)
        if value is not None:
            try:
                converted_value = value_type(value)
                data[field_name] = converted_value  # Update data with converted type
                if min_val is not None and converted_value < min_val:
                    errors[field_name] = f"'{field_name}' must be at least " \
                                         f"{min_val}."
                if max_val is not None and converted_value > max_val:
                    errors[field_name] = f"'{field_name}' must be at most " \
                                         f"{max_val}."
            except (ValueError, TypeError):
                errors[field_name] = f"'{field_name}' must be a valid " \
                                     f"{value_type.__name__}."
        return errors

    def _validate_regex_field(self, data: dict, field_name: str,
                              pattern: str) -> dict:
        """Validates a field against a regex pattern."""
        errors = {}
        value = data.get(field_name)
        if value is not None:
            if not isinstance(value, str):
                errors[field_name] = f"'{field_name}' must be a string to " \
                                     f"apply regex validation."
            elif not re.fullmatch(pattern, value):
                errors[field_name] = f"'{field_name}' has an invalid format."
        return errors

    def _validate_enum_field(self, data: dict, field_name: str,
                             allowed_values: set) -> dict:
        """
        Validates if a field's value is within a set of allowed values.
        """
        errors = {}
        value = data.get(field_name)
        if value is not None:
            if isinstance(value, str):
                if value not in allowed_values:
                    errors[field_name] = f"'{field_name}' has an invalid " \
                                         f"value '{value}'. Allowed values " \
                                         f"are: {', '.join(allowed_values)}."
            else:
                errors[field_name] = f"'{field_name}' must be a string and " \
                                     f"one of the allowed values: " \
                                     f"{', '.join(allowed_values)}."
        return errors

    def _validate_date_field(self, data: dict, field_name: str,
                             date_format: str = '%Y-%m-%d') -> dict:
        """
        Validates if a field is a valid date string and converts it to
        datetime.date object.
        """
        errors = {}
        value = data.get(field_name)
        if value is not None:
            try:
                # Attempt to parse as date, then store as datetime.date object
                data[field_name] = datetime.strptime(str(value),
                                                     date_format).date()
            except (ValueError, TypeError):
                errors[field_name] = f"'{field_name}' must be a valid date " \
                                     f"in '{date_format}' format."
        return errors

    def _validate_datetime_field(self, data: dict, field_name: str,
                                 datetime_format: str = '%Y-%m-%dT%H:%M:%S') \
                                 -> dict:
        """
        Validates if a field is a valid datetime string and converts it to
        datetime object.
        """
        errors = {}
        value = data.get(field_name)
        if value is not None:
            try:
                # Attempt to parse as datetime, then store as datetime object
                data[field_name] = datetime.strptime(str(value),
                                                     datetime_format)
            except (ValueError, TypeError):
                errors[field_name] = f"'{field_name}' must be a valid " \
                                     f"datetime in '{datetime_format}' format."
        return errors

    def _validate_uuid_field(self, data: dict, field_name: str) -> dict:
        """Validates if a field is a valid UUID string."""
        errors = {}
        value = data.get(field_name)
        if value is not None:
            if not isinstance(value, str):
                errors[field_name] = f"'{field_name}' must be a string."
            else:
                try:
                    uuid.UUID(value)
                except ValueError:
                    errors[field_name] = f"'{field_name}' is not a valid " \
                                         f"UUID format."
        return errors

    def validate_customer_data(self, customer_data: dict) -> tuple[bool, dict]:
        """
        Validates customer data based on defined rules.
        Modifies customer_data in place for type conversions (e.g., boolean,
        date).
        """
        errors = {}

        # Required fields for a new customer profile.
        # Assuming mobile, PAN, Aadhaar are primary identifiers for new records.
        required_fields = ['mobile_number', 'pan_number', 'aadhaar_number']
        errors.update(self._validate_required_fields(customer_data,
                                                     required_fields))

        # Validate format and type for specific fields
        errors.update(self._validate_uuid_field(customer_data, 'customer_id'))

        errors.update(self._validate_string_field(customer_data,
                                                  'mobile_number',
                                                  max_length=10))
        if 'mobile_number' not in errors:
            errors.update(self._validate_regex_field(customer_data,
                                                     'mobile_number',
                                                     self.MOBILE_NUMBER_REGEX))

        errors.update(self._validate_string_field(customer_data,
                                                  'pan_number',
                                                  max_length=10))
        if 'pan_number' not in errors:
            errors.update(self._validate_regex_field(customer_data,
                                                     'pan_number',
                                                     self.PAN_REGEX))

        errors.update(self._validate_string_field(customer_data,
                                                  'aadhaar_number',
                                                  max_length=12))
        if 'aadhaar_number' not in errors:
            errors.update(self._validate_regex_field(customer_data,
                                                     'aadhaar_number',
                                                     self.AADHAAR_REGEX))

        errors.update(self._validate_string_field(customer_data,
                                                  'ucid_number'))
        errors.update(self._validate_string_field(customer_data,
                                                  'loan_application_number'))

        errors.update(self._validate_boolean_field(customer_data, 'dnd_flag'))

        if 'segment' in customer_data and customer_data['segment'] is not None:
            errors.update(self._validate_string_field(customer_data,
                                                      'segment'))
            if 'segment' not in errors:
                errors.update(self._validate_enum_field(customer_data,
                                                        'segment',
                                                        self.ALLOWED_CUSTOMER_SEGMENTS))

        return not bool(errors), errors

    def validate_offer_data(self, offer_data: dict) -> tuple[bool, dict]:
        """
        Validates offer data based on defined rules.
        Modifies offer_data in place for type conversions (e.g., date).
        """
        errors = {}

        # Required fields for an offer
        required_fields = ['customer_id', 'offer_type', 'offer_status',
                           'start_date', 'end_date']
        errors.update(self._validate_required_fields(offer_data,
                                                     required_fields))

        # Validate format and type for specific fields
        errors.update(self._validate_uuid_field(offer_data, 'offer_id'))
        errors.update(self._validate_uuid_field(offer_data, 'customer_id'))

        errors.update(self._validate_enum_field(offer_data, 'offer_type',
                                                self.ALLOWED_OFFER_TYPES))
        errors.update(self._validate_enum_field(offer_data, 'offer_status',
                                                self.ALLOWED_OFFER_STATUSES))

        errors.update(self._validate_string_field(offer_data, 'propensity'))
        errors.update(self._validate_string_field(offer_data, 'channel'))

        errors.update(self._validate_date_field(offer_data, 'start_date'))
        errors.update(self._validate_date_field(offer_data, 'end_date'))

        # Cross-field validation: end_date must be after or equal to start_date
        if 'start_date' not in errors and 'end_date' not in errors:
            start_date = offer_data.get('start_date')
            end_date = offer_data.get('end_date')
            if start_date and end_date and end_date < start_date:
                errors['end_date'] = "End date cannot be before start date."

        return not bool(errors), errors

    def validate_event_data(self, event_data: dict) -> tuple[bool, dict]:
        """
        Validates event data based on defined rules.
        Modifies event_data in place for type conversions (e.g., datetime).
        """
        errors = {}

        # Required fields for an event
        required_fields = ['customer_id', 'event_type', 'event_source',
                           'event_timestamp']
        errors.update(self._validate_required_fields(event_data,
                                                     required_fields))

        # Validate format and type for specific fields
        errors.update(self._validate_uuid_field(event_data, 'event_id'))
        errors.update(self._validate_uuid_field(event_data, 'customer_id'))

        errors.update(self._validate_enum_field(event_data, 'event_type',
                                                self.ALLOWED_EVENT_TYPES))
        errors.update(self._validate_enum_field(event_data, 'event_source',
                                                self.ALLOWED_EVENT_SOURCES))

        # Use a common datetime format, e.g., ISO 8601.
        # System design uses '%Y-%m-%dT%H:%M:%S'
        errors.update(self._validate_datetime_field(event_data,
                                                    'event_timestamp',
                                                    datetime_format='%Y-%m-%dT%H:%M:%S'))

        # event_details is JSONB, so it can be any valid JSON.
        # If it's a string, it should be parsable as JSON.
        if 'event_details' in event_data and event_data['event_details'] is not None:
            if isinstance(event_data['event_details'], str):
                try:
                    event_data['event_details'] = json.loads(
                        event_data['event_details']
                    )
                except json.JSONDecodeError:
                    errors['event_details'] = "'event_details' string must " \
                                              "be a valid JSON format."
            elif not isinstance(event_data['event_details'], (dict, list)):
                errors['event_details'] = "'event_details' must be a " \
                                          "dictionary, list, or a JSON string."

        return not bool(errors), errors

    def validate_campaign_metric_data(self, metric_data: dict) -> tuple[bool, dict]:
        """
        Validates campaign metric data based on defined rules.
        Modifies metric_data in place for type conversions.
        """
        errors = {}

        required_fields = ['campaign_unique_id', 'campaign_name',
                           'campaign_date', 'attempted_count',
                           'sent_success_count', 'failed_count',
                           'conversion_rate']
        errors.update(self._validate_required_fields(metric_data,
                                                     required_fields))

        errors.update(self._validate_uuid_field(metric_data, 'metric_id'))
        errors.update(self._validate_string_field(metric_data,
                                                  'campaign_unique_id'))
        errors.update(self._validate_string_field(metric_data,
                                                  'campaign_name'))
        errors.update(self._validate_date_field(metric_data,
                                                'campaign_date'))

        errors.update(self._validate_numeric_field(metric_data,
                                                  'attempted_count',
                                                  value_type=int, min_val=0))
        errors.update(self._validate_numeric_field(metric_data,
                                                  'sent_success_count',
                                                  value_type=int, min_val=0))
        errors.update(self._validate_numeric_field(metric_data,
                                                  'failed_count',
                                                  value_type=int, min_val=0))
        errors.update(self._validate_numeric_field(metric_data,
                                                  'conversion_rate',
                                                  value_type=float,
                                                  min_val=0.0, max_val=100.0))

        # Cross-field validation: sent_success_count + failed_count <= attempted_count
        if all(k not in errors for k in ['attempted_count',
                                         'sent_success_count',
                                         'failed_count']):
            attempted = metric_data.get('attempted_count', 0)
            sent_success = metric_data.get('sent_success_count', 0)
            failed = metric_data.get('failed_count', 0)
            if (sent_success + failed) > attempted:
                errors['counts'] = "Sum of sent_success_count and " \
                                   "failed_count cannot exceed attempted_count."

        return not bool(errors), errors

    def validate_ingestion_log_data(self, log_data: dict) -> tuple[bool, dict]:
        """
        Validates ingestion log data.
        Modifies log_data in place for type conversions.
        """
        errors = {}

        required_fields = ['file_name', 'status']
        errors.update(self._validate_required_fields(log_data,
                                                     required_fields))

        errors.update(self._validate_uuid_field(log_data, 'log_id'))
        errors.update(self._validate_string_field(log_data, 'file_name'))
        errors.update(self._validate_enum_field(log_data, 'status',
                                                self.ALLOWED_INGESTION_STATUSES))
        errors.update(self._validate_string_field(log_data,
                                                  'error_description'))

        # upload_timestamp is typically generated by the system, but if
        # provided, validate it.
        errors.update(self._validate_datetime_field(log_data,
                                                    'upload_timestamp',
                                                    datetime_format='%Y-%m-%dT%H:%M:%S'))

        return not bool(errors), errors