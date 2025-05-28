import pandas as pd
import io
import base64
import logging
import re
from typing import List, Dict, Tuple, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define expected columns and their validation rules
# This is a simplified set based on the database schema and FRs.
# In a real project, these rules might be loaded from a configuration
# or database for easier management and flexibility.
EXPECTED_COLUMNS = {
    "mobile_number": {"required": True, "type": str, "min_len": 10, "max_len": 10, "regex": r"^\d{10}$"},
    "pan": {"required": False, "type": str, "min_len": 10, "max_len": 10, "regex": r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"},
    "aadhaar_ref_number": {"required": False, "type": str, "min_len": 12, "max_len": 12, "regex": r"^\d{12}$"},
    "ucid": {"required": False, "type": str},
    "previous_loan_app_number": {"required": False, "type": str},
    "customer_segment": {"required": False, "type": str, "allowed_values": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]}, # FR19
    "is_dnd": {"required": False, "type": bool, "default": False}, # FR21
    "loan_type": {"required": True, "type": str, "allowed_values": ["Prospect", "TW Loyalty", "Topup", "Employee"]}, # FR29
    # Additional common customer attributes that might be in the file
    "email": {"required": False, "type": str},
    "first_name": {"required": False, "type": str},
    "last_name": {"required": False, "type": str},
    "dob": {"required": False, "type": str}, # Date of Birth, will need proper date parsing/validation
    "address": {"required": False, "type": str},
    "city": {"required": False, "type": str},
    "state": {"required": False, "type": str},
    "pincode": {"required": False, "type": str, "min_len": 6, "max_len": 6, "regex": r"^\d{6}$"},
}

# Map file_type from API request to the expected 'loan_type' value in the file
FILE_TYPE_TO_LOAN_TYPE = {
    "Prospect": "Prospect",
    "TW Loyalty": "TW Loyalty",
    "Topup": "Topup",
    "Employee loans": "Employee", # Assuming "Employee loans" maps to "Employee"
}

def _validate_row(row: Dict[str, Any], row_index: int, file_type_context: str) -> Tuple[bool, str]:
    """
    Performs basic column-level validation for a single row.
    Returns (is_valid, error_message).
    """
    errors = []

    # Check for required columns based on EXPECTED_COLUMNS
    for col, rules in EXPECTED_COLUMNS.items():
        if rules.get("required") and pd.isna(row.get(col)):
            errors.append(f"Missing required column: '{col}'")

    # Specific validation for 'loan_type' based on the uploaded file_type_context
    expected_loan_type = FILE_TYPE_TO_LOAN_TYPE.get(file_type_context)
    if expected_loan_type:
        actual_loan_type = row.get("loan_type")
        if pd.isna(actual_loan_type) or str(actual_loan_type).strip().lower() != expected_loan_type.lower():
            errors.append(f"Invalid 'loan_type'. Expected '{expected_loan_type}' for file type '{file_type_context}', but got '{actual_loan_type}'")
    else:
        errors.append(f"Unknown file type context '{file_type_context}'. Cannot validate 'loan_type'.")


    # Perform type, length, and regex validation for relevant columns
    for col, rules in EXPECTED_COLUMNS.items():
        value = row.get(col)
        if pd.isna(value):
            continue # Skip further validation if value is missing and not required

        # Type validation
        if "type" in rules:
            if rules["type"] == bool:
                if not isinstance(value, (bool, str, int, float)):
                    errors.append(f"Column '{col}' must be boolean (True/False, 1/0, 'True'/'False'). Got '{value}'")
                elif isinstance(value, str) and value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    errors.append(f"Column '{col}' must be 'True'/'False' or '1'/'0'. Got '{value}'")
            elif rules["type"] == str:
                if not isinstance(value, str):
                    # Attempt to convert to string for further validation if possible
                    try:
                        value = str(value)
                        row[col] = value # Update row with string conversion
                    except Exception:
                        errors.append(f"Column '{col}' must be a string. Got '{value}'")
                        continue # Skip further string validations for this column
                
                # Length validation
                if "min_len" in rules and len(value) < rules["min_len"]:
                    errors.append(f"Column '{col}' too short (min {rules['min_len']} chars). Got '{value}'")
                if "max_len" in rules and len(value) > rules["max_len"]:
                    errors.append(f"Column '{col}' too long (max {rules['max_len']} chars). Got '{value}'")
                
                # Regex validation
                if "regex" in rules:
                    if not re.match(rules["regex"], value):
                        errors.append(f"Column '{col}' has invalid format. Got '{value}'")
            # Add other type validations (e.g., int, float, date) as needed
            # For 'dob', a more robust date parsing and validation would be needed here.

        # Allowed values validation
        if "allowed_values" in rules and value not in rules["allowed_values"]:
            errors.append(f"Column '{col}' has invalid value '{value}'. Allowed values are: {', '.join(rules['allowed_values'])}")

    if errors:
        return False, "; ".join(errors)
    return True, ""

def parse_customer_file(file_content_base64: str, file_type: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Parses a base64 encoded customer details file (CSV or Excel),
    performs basic validation, and separates valid from invalid records.

    Args:
        file_content_base64 (str): Base64 encoded content of the file.
        file_type (str): Type of the file, e.g., "Prospect", "TW Loyalty", "Topup", "Employee loans".
                         This is used to validate the 'loan_type' column within the file.

    Returns:
        Tuple[List[Dict], List[Dict]]: A tuple containing:
            - List of dictionaries for valid records.
            - List of dictionaries for invalid records, each with an 'Error Desc' key.
    """
    valid_records = []
    error_records = []

    try:
        decoded_content = base64.b64decode(file_content_base64)
        file_stream = io.BytesIO(decoded_content)

        df = None
        # Attempt to read as CSV first, then Excel
        try:
            df = pd.read_csv(file_stream)
            logger.info("File identified and parsed as CSV.")
        except Exception as csv_e:
            file_stream.seek(0) # Reset stream position
            try:
                df = pd.read_excel(file_stream)
                logger.info("File identified and parsed as Excel.")
            except Exception as excel_e:
                logger.error(f"Could not parse file as CSV ({csv_e}) or Excel ({excel_e}).")
                error_records.append({"Error Desc": f"File format not supported or corrupted. Please upload a valid CSV or Excel file."})
                return [], error_records

        if df is None:
            error_records.append({"Error Desc": "Failed to read file content."})
            return [], error_records

        # Normalize column names: strip whitespace, convert to lowercase, replace non-alphanumeric with underscore
        df.columns = df.columns.str.strip().str.lower().str.replace(r'[^a-zA-Z0-9_]', '', regex=True)

        # Check if all required columns (from EXPECTED_COLUMNS) are present in the uploaded file
        # Note: This checks for required columns *in the file*, not just those that are required for the DB.
        # The _validate_row function handles missing values for required columns.
        file_columns = set(df.columns)
        missing_file_cols = [col for col, rules in EXPECTED_COLUMNS.items() if rules.get("required") and col not in file_columns]
        if missing_file_cols:
            error_records.append({"Error Desc": f"Missing critical columns in file: {', '.join(missing_file_cols)}. Please ensure all required headers are present."})
            return [], error_records

        # Process each row for validation
        temp_valid_records = []
        for index, row_series in df.iterrows():
            row_dict = row_series.to_dict()
            original_row_data = row_dict.copy() # Keep original for error reporting

            # Pre-process 'is_dnd' to boolean
            if 'is_dnd' in row_dict and not pd.isna(row_dict['is_dnd']):
                if isinstance(row_dict['is_dnd'], str):
                    row_dict['is_dnd'] = row_dict['is_dnd'].lower() in ['true', '1', 'yes']
                elif isinstance(row_dict['is_dnd'], (int, float)):
                    row_dict['is_dnd'] = bool(row_dict['is_dnd'])
                else:
                    # If it's not a recognized boolean value, set to default and let validation handle it
                    row_dict['is_dnd'] = EXPECTED_COLUMNS['is_dnd']['default']
            else:
                row_dict['is_dnd'] = EXPECTED_COLUMNS['is_dnd']['default'] # Apply default if missing or NaN

            is_valid, error_msg = _validate_row(row_dict, index + 2, file_type) # +2 for 1-based index and header row

            if is_valid:
                # Prepare data for insertion: filter to expected columns and collect others into customer_attributes
                processed_row = {}
                customer_attributes = {}
                for col_name, value in row_dict.items():
                    if col_name in EXPECTED_COLUMNS:
                        # Ensure values are not NaN for expected columns before assigning
                        processed_row[col_name] = value if not pd.isna(value) else None
                    elif not pd.isna(value):
                        # Collect other columns into customer_attributes JSONB
                        customer_attributes[col_name] = value

                processed_row['customer_attributes'] = customer_attributes
                temp_valid_records.append(processed_row)
            else:
                # Add 'Error Desc' to the original row data for the error file
                original_row_data['Error Desc'] = error_msg
                error_records.append(original_row_data)

        # Perform in-batch deduplication based on mobile_number (FR3, FR4 are system-wide, this is file-level)
        unique_mobile_numbers_in_batch = set()
        for record in temp_valid_records:
            mobile = record.get('mobile_number')
            if mobile:
                if mobile not in unique_mobile_numbers_in_batch:
                    unique_mobile_numbers_in_batch.add(mobile)
                    valid_records.append(record)
                else:
                    record_for_error = record.copy()
                    record_for_error['Error Desc'] = f"Duplicate mobile number '{mobile}' within the uploaded file."
                    error_records.append(record_for_error)
            else:
                # This case should ideally be caught by required field validation, but as a fallback
                record_for_error = record.copy()
                record_for_error['Error Desc'] = "Missing mobile number (should have been caught by validation)."
                error_records.append(record_for_error)

        return valid_records, error_records

    except Exception as e:
        logger.exception(f"An unexpected error occurred during file parsing: {e}")
        error_records.append({"Error Desc": f"An unexpected server error occurred during file processing: {e}"})
        return [], error_records