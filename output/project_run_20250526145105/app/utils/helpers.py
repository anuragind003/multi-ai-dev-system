import uuid
import re
import io
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import UploadFile
from starlette.responses import StreamingResponse
from dateutil.relativedelta import relativedelta

# --- UUID Generation ---
def generate_uuid() -> str:
    """Generates a new UUID (Universally Unique Identifier)."""
    return str(uuid.uuid4())

# --- Identifier Normalization ---
def normalize_mobile_number(mobile: Optional[str]) -> Optional[str]:
    """
    Normalizes a mobile number by removing non-digit characters.
    Returns None if input is None or empty after normalization.
    """
    if not mobile:
        return None
    normalized = re.sub(r'\D', '', mobile)
    return normalized if normalized else None

def normalize_pan_number(pan: Optional[str]) -> Optional[str]:
    """
    Normalizes a PAN number by converting to uppercase and removing spaces.
    Returns None if input is None or empty after normalization.
    """
    if not pan:
        return None
    normalized = pan.strip().upper().replace(" ", "")
    return normalized if normalized else None

def normalize_aadhaar_number(aadhaar: Optional[str]) -> Optional[str]:
    """
    Normalizes an Aadhaar number by removing spaces and dashes.
    Returns None if input is None or empty after normalization.
    """
    if not aadhaar:
        return None
    normalized = aadhaar.strip().replace(" ", "").replace("-", "")
    return normalized if normalized else None

def normalize_ucid_number(ucid: Optional[str]) -> Optional[str]:
    """
    Normalizes a UCID number by stripping whitespace.
    Returns None if input is None or empty after normalization.
    """
    if not ucid:
        return None
    normalized = ucid.strip()
    return normalized if normalized else None

def normalize_loan_application_number(loan_app_num: Optional[str]) -> Optional[str]:
    """
    Normalizes a loan application number by stripping whitespace.
    Returns None if input is None or empty after normalization.
    """
    if not loan_app_num:
        return None
    normalized = loan_app_num.strip()
    return normalized if normalized else None

# --- Basic Data Validation ---
def is_valid_mobile_number(mobile: Optional[str]) -> bool:
    """
    Checks if a normalized mobile number is valid (10 digits).
    """
    normalized = normalize_mobile_number(mobile)
    return bool(normalized and len(normalized) == 10 and normalized.isdigit())

def is_valid_pan_number(pan: Optional[str]) -> bool:
    """
    Checks if a normalized PAN number is valid (5 letters, 4 digits, 1 letter).
    """
    normalized = normalize_pan_number(pan)
    if not normalized:
        return False
    # PAN format: ABCDE1234F (5 letters, 4 digits, 1 letter)
    return bool(re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', normalized))

def is_valid_aadhaar_number(aadhaar: Optional[str]) -> bool:
    """
    Checks if a normalized Aadhaar number is valid (12 digits).
    """
    normalized = normalize_aadhaar_number(aadhaar)
    return bool(normalized and len(normalized) == 12 and normalized.isdigit())

def is_valid_date_format(date_str: Optional[str], date_format: str = "%Y-%m-%d") -> bool:
    """
    Checks if a string matches a given date format.
    """
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False

# --- File Handling (CSV/Excel) ---
async def read_csv_from_upload_file(file: UploadFile) -> pd.DataFrame:
    """
    Reads a CSV file from an UploadFile object into a pandas DataFrame.
    Raises ValueError if the file is not a CSV or cannot be parsed.
    """
    if not file.filename or not file.filename.lower().endswith(('.csv')):
        raise ValueError("Uploaded file must be a CSV.")

    try:
        contents = await file.read()
        # Attempt to decode with utf-8, fall back to latin-1 if utf-8 fails
        try:
            s_io = io.StringIO(contents.decode('utf-8'))
        except UnicodeDecodeError:
            s_io = io.StringIO(contents.decode('latin-1'))

        df = pd.read_csv(s_io)
        return df
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

def create_csv_response(df: pd.DataFrame, filename: str = "data.csv") -> StreamingResponse:
    """
    Creates a FastAPI StreamingResponse for downloading a pandas DataFrame as a CSV file.
    """
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    return response

def create_excel_response(df: pd.DataFrame, filename: str = "data.xlsx") -> StreamingResponse:
    """
    Creates a FastAPI StreamingResponse for downloading a pandas DataFrame as an Excel file.
    Requires 'openpyxl' to be installed (e.g., pip install openpyxl).
    """
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close() # Use .close() for pandas >= 1.3.0, .save() for older versions
    output.seek(0)

    response = StreamingResponse(
        iter([output.read()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    return response

# --- Data Transformation/Mapping (Generic) ---
def map_dict_keys(data: Dict[str, Any], key_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Maps keys in a dictionary based on a provided mapping.
    Keys not in the mapping are retained.
    """
    mapped_data = {}
    for old_key, new_key in key_mapping.items():
        if old_key in data:
            mapped_data[new_key] = data[old_key]
    # Retain keys not in mapping
    for key, value in data.items():
        if key not in key_mapping.keys():
            mapped_data[key] = value
    return mapped_data

# --- Date/Time Utilities ---
def get_current_timestamp() -> datetime:
    """Returns the current UTC timestamp with timezone information."""
    return datetime.now(tz=timezone.utc)

def get_n_months_ago(n_months: int) -> datetime:
    """
    Calculates a datetime object representing 'n_months' ago from the current UTC time.
    Used for data retention policies (e.g., 3 months, 6 months).
    """
    return datetime.now(tz=timezone.utc) - relativedelta(months=n_months)