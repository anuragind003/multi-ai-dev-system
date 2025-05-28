import io
import pandas as pd
from flask import Response, current_app
from typing import Tuple, Dict, List, Any

# Define expected columns for different file types based on FR1 and general context.
# This dictionary serves as a schema for basic column-level validation.
# In a real-world scenario, this might be loaded from a configuration file or a database.
EXPECTED_COLUMNS_MAP: Dict[str, List[str]] = {
    "Prospect": [
        "mobile_number", "pan", "aadhaar_ref_number", "first_name", "last_name",
        "email", "address", "city", "state", "pincode", "loan_amount_requested",
        "product_type"
    ],
    "TW Loyalty": [
        "mobile_number", "customer_id", "previous_loan_app_number", "offer_id",
        "loan_amount_eligible", "interest_rate", "tenure", "offer_expiry_date"
    ],
    "Topup": [
        "mobile_number", "pan", "ucid", "previous_loan_app_number", "current_loan_balance",
        "topup_amount_eligible", "offer_id", "offer_expiry_date"
    ],
    "Employee loans": [
        "employee_id", "mobile_number", "pan", "aadhaar_ref_number", "loan_amount_requested",
        "designation", "department", "offer_id", "offer_expiry_date"
    ]
}

def read_uploaded_file(file_content_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Reads an uploaded file (CSV or Excel) into a pandas DataFrame.
    Supports .csv, .xls, and .xlsx extensions.

    Args:
        file_content_bytes: The raw bytes content of the uploaded file.
        filename: The original filename, used to determine the file type.

    Returns:
        A pandas DataFrame containing the file's data.

    Raises:
        ValueError: If the file type is unsupported or reading fails.
    """
    logger = current_app.logger
    try:
        file_extension = filename.split('.')[-1].lower()
        if file_extension == 'csv':
            df = pd.read_csv(io.BytesIO(file_content_bytes))
        elif file_extension in ['xls', 'xlsx']:
            df = pd.read_excel(io.BytesIO(file_content_bytes))
        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Only CSV and Excel are supported.")
        logger.info(f"Successfully read file: {filename} with {len(df)} rows.")
        return df
    except Exception as e:
        logger.error(f"Error reading uploaded file '{filename}': {e}")
        raise ValueError(f"Failed to read file '{filename}': {e}")

def validate_customer_data_columns(df: pd.DataFrame, file_type: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Performs basic column-level validation on the DataFrame based on the file type.
    It checks for the presence of expected columns and performs basic data integrity checks
    on key identifiers like mobile_number and PAN.

    Args:
        df: The pandas DataFrame to validate.
        file_type: A string indicating the type of file (e.g., 'Prospect', 'Topup').

    Returns:
        A tuple containing two pandas DataFrames:
        - valid_df: Rows that passed all validations.
        - error_df: Rows that failed validation, with an 'Error Desc' column explaining the failure.
    """
    logger = current_app.logger
    expected_columns = EXPECTED_COLUMNS_MAP.get(file_type)

    if not expected_columns:
        logger.warning(f"No specific column validation defined for file type: '{file_type}'. Skipping detailed column validation.")
        # If no specific columns are defined, consider all rows valid for this step,
        # but add an empty 'Error Desc' column for consistency in downstream processing.
        df_copy = df.copy()
        df_copy['Error Desc'] = ''
        return df_copy, pd.DataFrame(columns=df.columns.tolist() + ['Error Desc'])

    # Check for missing required columns
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        error_message = f"Missing required columns for '{file_type}' file: {', '.join(missing_columns)}"
        logger.error(error_message)
        # If critical columns are missing, all rows are effectively invalid for processing.
        # Create an error DataFrame with all original rows and the error message.
        error_df_all = df.copy()
        error_df_all['Error Desc'] = error_message
        return pd.DataFrame(columns=df.columns), error_df_all # Return empty valid_df

    errors = []
    valid_rows = []

    # Perform row-level basic validation
    for index, row in df.iterrows():
        row_errors = []

        # Example validation: mobile_number must be present and numeric
        if 'mobile_number' in row and (pd.isna(row['mobile_number']) or not str(row['mobile_number']).strip().isdigit()):
            row_errors.append("Invalid or missing 'mobile_number'.")
        
        # Example validation: PAN must be present for certain types if column exists
        if 'pan' in row and file_type in ["Prospect", "Topup", "Employee loans"] and pd.isna(row['pan']):
            row_errors.append("Missing 'pan' for this file type.")

        # Add more specific validations here as per FR1 and detailed schema
        # e.g., check for Aadhaar format, email format, date formats, etc.

        if row_errors:
            row_dict = row.to_dict()
            row_dict['Error Desc'] = "; ".join(row_errors)
            errors.append(row_dict)
        else:
            valid_rows.append(row.to_dict())

    valid_df = pd.DataFrame(valid_rows)
    error_df = pd.DataFrame(errors)

    logger.info(f"Validation complete for '{file_type}' file. Valid rows: {len(valid_df)}, Error rows: {len(error_df)}")
    return valid_df, error_df

def generate_csv_response(df: pd.DataFrame, filename: str) -> Response:
    """
    Generates a Flask Response object for downloading a DataFrame as a CSV file.

    Args:
        df: The pandas DataFrame to convert to CSV.
        filename: The desired base filename for the download (e.g., "moengage_data").

    Returns:
        A Flask Response object configured for CSV file download.
    """
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0) # Rewind the buffer to the beginning

    response = Response(csv_buffer.getvalue(), mimetype='text/csv')
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
    current_app.logger.info(f"Generated CSV response for '{filename}.csv' with {len(df)} rows.")
    return response

def generate_excel_response(df: pd.DataFrame, filename: str) -> Response:
    """
    Generates a Flask Response object for downloading a DataFrame as an Excel (XLSX) file.

    Args:
        df: The pandas DataFrame to convert to Excel.
        filename: The desired base filename for the download (e.g., "duplicate_data").

    Returns:
        A Flask Response object configured for Excel file download.
    """
    excel_buffer = io.BytesIO()
    # Use xlsxwriter engine for better compatibility and features if needed
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    excel_buffer.seek(0) # Rewind the buffer to the beginning

    response = Response(excel_buffer.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.xlsx"
    current_app.logger.info(f"Generated Excel response for '{filename}.xlsx' with {len(df)} rows.")
    return response