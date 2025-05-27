import re
from datetime import datetime

class DataValidationService:
    """
    Service for performing column-level data validation based on predefined rules.
    This service is designed to be used for validating incoming data,
    such as from file uploads (Offermart) or real-time API payloads.
    """

    def __init__(self):
        # Regex patterns for common Indian identifiers
        # Assumes 10-digit mobile numbers starting with 6, 7, 8, or 9
        self.MOBILE_PATTERN = re.compile(r"^[6-9]\d{9}$")
        # Assumes standard PAN format: 5 uppercase alphabets, 4 digits, 1 uppercase alphabet
        self.PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
        # Assumes 12-digit Aadhaar number
        self.AADHAAR_PATTERN = re.compile(r"^\d{12}$")
        # UCID and Loan Application Number formats are not specified,
        # so basic string validation will apply unless specific patterns are added.

    def _is_not_empty(self, value):
        """Checks if a value is not None and not an empty string after stripping whitespace."""
        return value is not None and str(value).strip() != ""

    def _is_valid_mobile(self, value):
        """Checks if the value matches the mobile number pattern."""
        if not isinstance(value, str):
            return False
        return self.MOBILE_PATTERN.match(value) is not None

    def _is_valid_pan(self, value):
        """Checks if the value matches the PAN number pattern."""
        if not isinstance(value, str):
            return False
        return self.PAN_PATTERN.match(value.upper()) is not None

    def _is_valid_aadhaar(self, value):
        """Checks if the value matches the Aadhaar number pattern."""
        if not isinstance(value, str):
            return False
        return self.AADHAAR_PATTERN.match(value) is not None

    def _is_valid_date(self, value, date_format="%Y-%m-%d"):
        """Checks if a string value can be parsed into a date using the given format."""
        if not isinstance(value, str):
            return False
        try:
            datetime.strptime(value, date_format)
            return True
        except ValueError:
            return False

    def _is_valid_datetime(self, value, datetime_format="%Y-%m-%d %H:%M:%S"):
        """Checks if a string value can be parsed into a datetime using the given format."""
        if not isinstance(value, str):
            return False
        try:
            datetime.strptime(value, datetime_format)
            return True
        except ValueError:
            return False

    def _is_valid_boolean(self, value):
        """Checks if a value can be interpreted as a boolean."""
        if isinstance(value, bool):
            return True
        if isinstance(value, str):
            return value.lower() in ['true', 'false', '1', '0', 'yes', 'no']
        if isinstance(value, int):
            return value in [0, 1]
        return False

    def _is_valid_integer(self, value):
        """Checks if a value can be converted to an integer."""
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    def _is_valid_numeric(self, value):
        """Checks if a value can be converted to a float (for numeric types like decimal/numeric)."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _is_in_enum(self, value, enum_values):
        """Checks if a value is present in a list of allowed enum values (case-sensitive)."""
        if value is None:
            return False
        return str(value).strip() in enum_values

    def validate_record(self, record: dict, rules: dict) -> list:
        """
        Validates a single data record (dictionary) against a set of predefined rules.

        Args:
            record (dict): The data record to validate (e.g., a row from a CSV or a JSON payload).
            rules (dict): A dictionary where keys are field names and values are
                          dictionaries defining validation rules for that field.
                          Each field's rules can include:
                          - "required": bool (True if the field must not be empty)
                          - "type": str (e.g., "string", "mobile", "pan", "aadhaar", "date",
                                         "datetime", "boolean", "integer", "numeric", "enum")
                          - "min_length": int (for "string" type)
                          - "max_length": int (for "string" type)
                          - "values": list (for "enum" type, list of allowed string values)
                          - "date_format": str (for "date" type, e.g., "%Y-%m-%d")
                          - "datetime_format": str (for "datetime" type, e.g., "%Y-%m-%d %H:%M:%S")

        Returns:
            list: A list of error messages (strings). Returns an empty list if no errors are found.
        """
        errors = []
        for field, field_rules in rules.items():
            value = record.get(field)
            field_name_display = field.replace('_', ' ').title() # For more readable error messages

            # 1. Check for required fields
            if field_rules.get("required") and not self._is_not_empty(value):
                errors.append(f"'{field_name_display}' is required and cannot be empty.")
                continue # Skip further validation for this field if it's missing

            # If not required and value is empty, no further validation is needed for this field
            if not field_rules.get("required") and not self._is_not_empty(value):
                continue

            # 2. Type-specific validations
            field_type = field_rules.get("type")
            if field_type == "string":
                if not isinstance(value, str):
                    errors.append(f"'{field_name_display}' must be a string.")
                else:
                    if "min_length" in field_rules and len(value) < field_rules["min_length"]:
                        errors.append(f"'{field_name_display}' must be at least {field_rules['min_length']} characters long.")
                    if "max_length" in field_rules and len(value) > field_rules["max_length"]:
                        errors.append(f"'{field_name_display}' cannot exceed {field_rules['max_length']} characters.")
            elif field_type == "mobile":
                if not self._is_valid_mobile(value):
                    errors.append(f"'{field_name_display}' must be a valid 10-digit mobile number.")
            elif field_type == "pan":
                if not self._is_valid_pan(value):
                    errors.append(f"'{field_name_display}' must be a valid PAN number (e.g., ABCDE1234F).")
            elif field_type == "aadhaar":
                if not self._is_valid_aadhaar(value):
                    errors.append(f"'{field_name_display}' must be a valid 12-digit Aadhaar number.")
            elif field_type == "date":
                date_format = field_rules.get("date_format", "%Y-%m-%d")
                if not self._is_valid_date(value, date_format):
                    errors.append(f"'{field_name_display}' must be a valid date in '{date_format}' format.")
            elif field_type == "datetime":
                datetime_format = field_rules.get("datetime_format", "%Y-%m-%d %H:%M:%S")
                if not self._is_valid_datetime(value, datetime_format):
                    errors.append(f"'{field_name_display}' must be a valid datetime in '{datetime_format}' format.")
            elif field_type == "boolean":
                if not self._is_valid_boolean(value):
                    errors.append(f"'{field_name_display}' must be a boolean value (e.g., True/False, 1/0, Yes/No).")
            elif field_type == "integer":
                if not self._is_valid_integer(value):
                    errors.append(f"'{field_name_display}' must be an integer.")
            elif field_type == "numeric":
                if not self._is_valid_numeric(value):
                    errors.append(f"'{field_name_display}' must be a numeric value.")
            elif field_type == "enum":
                enum_values = field_rules.get("values")
                if not enum_values:
                    errors.append(f"Validation rule for '{field_name_display}' is missing 'values' for enum type.")
                elif not self._is_in_enum(value, enum_values):
                    errors.append(f"'{field_name_display}' must be one of: {', '.join(enum_values)}.")
            # Add more custom type validations here as needed (e.g., UUID, email, URL)

        return errors