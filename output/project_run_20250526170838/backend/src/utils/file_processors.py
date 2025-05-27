import csv
import io
import base64
import uuid
from datetime import datetime
import json

# Define expected columns for customer data upload from the CSV file.
# These are the fields that the file processor expects to find in the uploaded CSV.
# Additional fields like 'loan_type' and 'source_channel' are passed separately
# to the processing function as context for the entire file.
EXPECTED_CUSTOMER_CSV_COLUMNS = [
    "mobile_number",
    "pan_number",
    "aadhaar_number",
    "ucid_number",
    "loan_application_number",
    "first_name",
    "last_name",
    "email",
    "address",
    "city",
    "state",
    "pincode",
    "dnd_flag",
    "segment"
]

def validate_customer_row(row_data: dict, row_num: int) -> tuple[bool, str]:
    """
    Performs basic column-level validation on a single row of customer data.
    This includes checking for required identifiers and basic format validation.

    Args:
        row_data (dict): A dictionary representing a single row of customer data.
                         Keys are normalized (lowercase, stripped).
        row_num (int): The 1-based row number in the original CSV file (including header).

    Returns:
        tuple[bool, str]: A tuple where the first element is True if the row is valid,
                          False otherwise. The second element is an error message string
                          if validation fails, or an empty string if valid.
    """
    errors = []

    # FR1, NFR3: Basic column-level validation.
    # Check for essential identifiers (at least one must be present for deduplication).
    # These are critical for identifying and deduplicating customers (FR3, FR4, FR5, FR6).
    identifiers = [
        row_data.get("mobile_number"),
        row_data.get("pan_number"),
        row_data.get("aadhaar_number"),
        row_data.get("ucid_number"),
        row_data.get("loan_application_number")
    ]
    if not any(val and val.strip() for val in identifiers):
        errors.append("At least one identifier (mobile, PAN, Aadhaar, UCID, LAN) is required.")

    # Basic format validation for mobile number (if present and not empty)
    mobile = row_data.get("mobile_number")
    if mobile and mobile.strip():
        mobile_stripped = mobile.strip()
        # Assuming 10-digit mobile numbers for Indian context
        if not mobile_stripped.isdigit() or len(mobile_stripped) != 10:
            errors.append("Mobile number must be 10 digits.")

    # Basic format validation for PAN (if present and not empty)
    pan = row_data.get("pan_number")
    if pan and pan.strip():
        pan_stripped = pan.strip()
        # Assuming 10-character alphanumeric PAN for Indian context
        if len(pan_stripped) != 10 or not pan_stripped.isalnum():
            errors.append("PAN number must be 10 alphanumeric characters.")

    # Basic format validation for Aadhaar (if present and not empty)
    aadhaar = row_data.get("aadhaar_number")
    if aadhaar and aadhaar.strip():
        aadhaar_stripped = aadhaar.strip()
        # Assuming 12-digit Aadhaar numbers
        if not aadhaar_stripped.isdigit() or len(aadhaar_stripped) != 12:
            errors.append("Aadhaar number must be 12 digits.")

    # DND flag validation (if present and not empty)
    dnd_flag = row_data.get("dnd_flag")
    if dnd_flag and dnd_flag.strip():
        dnd_flag_lower = dnd_flag.strip().lower()
        # Accept common boolean representations
        if dnd_flag_lower not in ['true', 'false', '1', '0', 'yes', 'no']:
            errors.append("DND flag must be 'true', 'false', '1', '0', 'yes', or 'no'.")

    return not bool(errors), "; ".join(errors)

def process_customer_upload_file(
    file_content_base64: str,
    file_name: str,
    loan_type: str,
    db_session, # Expected: SQLAlchemy session object (e.g., db.session)
    CustomerModel, # Expected: SQLAlchemy Customer model class (e.g., from backend.src.models.customer)
    IngestionLogModel, # Expected: SQLAlchemy IngestionLog model class (e.g., from backend.src.models.ingestion_log)
    customer_service_create_or_update # Expected: A function from customer_service module
                                      # that handles customer creation/deduplication/update.
                                      # (e.g., from backend.src.services.customer_service)
) -> dict:
    """
    Processes a base64 encoded CSV file containing customer data uploaded via the Admin Portal.
    (FR35: Admin Portal allows uploading customer details).
    It performs row-level validation, attempts to create/update customers (FR36: generates leads),
    and logs the overall ingestion status and row-level errors.

    Args:
        file_content_base64 (str): Base64 encoded content of the CSV file.
        file_name (str): The original name of the uploaded file.
        loan_type (str): The type of loan associated with the uploaded data (e.g., 'Prospect', 'TW Loyalty').
        db_session: The database session object (e.g., from Flask-SQLAlchemy).
        CustomerModel: The SQLAlchemy model for the 'customers' table.
        IngestionLogModel: The SQLAlchemy model for the 'ingestion_logs' table.
        customer_service_create_or_update: A callable function that takes db_session, CustomerModel,
                                           and a dictionary of customer data, and handles the
                                           deduplication and persistence logic.

    Returns:
        dict: A dictionary containing the processing status, log ID, success count, and error count.
              Example: {"status": "success", "log_id": "...", "success_count": 10, "error_count": 0}
              On failure, it includes a "message" field.
    """
    log_id = str(uuid.uuid4())
    success_count = 0
    error_count = 0
    row_error_details = [] # Collects details for rows that failed processing (for FR38, FR34)

    # Create an initial ingestion log entry with status 'PROCESSING'.
    # This ensures that even if file parsing fails immediately, there's a record.
    ingestion_log = IngestionLogModel(
        log_id=log_id,
        file_name=file_name,
        upload_timestamp=datetime.utcnow(),
        status="PROCESSING",
        error_description=None, # Will be updated on overall failure
        success_count=0,
        error_count=0,
        error_details_json=None # Will store JSON string of row_error_details
    )
    db_session.add(ingestion_log)
    try:
        db_session.commit() # Persist the initial log entry
    except Exception as e:
        db_session.rollback()
        return {
            "status": "error",
            "log_id": log_id,
            "success_count": 0,
            "error_count": 0,
            "message": f"Failed to create initial ingestion log entry: {str(e)}"
        }

    try:
        # Decode the base64 content and prepare for CSV parsing
        decoded_content = base64.b64decode(file_content_base64)
        csv_file = io.StringIO(decoded_content.decode('utf-8'))
        reader = csv.DictReader(csv_file)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no headers.")

        # Normalize CSV headers (strip whitespace and convert to lowercase)
        reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]

        # Check if any of the expected customer columns are present in the headers.
        # This is a basic check to ensure the file is relevant.
        if not any(col in reader.fieldnames for col in EXPECTED_CUSTOMER_CSV_COLUMNS):
            raise ValueError(f"CSV file must contain at least one of the following relevant columns: {', '.join(EXPECTED_CUSTOMER_CSV_COLUMNS)}")

        # Process each row in the CSV file
        for i, row in enumerate(reader):
            row_num = i + 2 # Calculate 1-based row number, accounting for 0-indexed loop and header row
            # Normalize row data keys (strip whitespace and convert to lowercase)
            processed_row_data = {k.strip().lower(): v.strip() for k, v in row.items()}

            # Add context-specific data not necessarily present in the CSV
            processed_row_data['loan_type'] = loan_type
            processed_row_data['source_channel'] = f"AdminUpload_{loan_type}" # Default source for admin uploads

            # Perform row-level validation
            is_valid, validation_error = validate_customer_row(processed_row_data, row_num)

            if not is_valid:
                error_count += 1
                row_error_details.append({
                    "row_number": row_num,
                    "data": processed_row_data,
                    "error_description": validation_error
                })
                continue # Skip to the next row if validation fails

            try:
                # Call the customer service to handle the actual data persistence and deduplication.
                # This function is responsible for FR3, FR4, FR5, FR6 (deduplication)
                # and FR36 (generating leads/updating customer profiles).
                customer_service_create_or_update(db_session, CustomerModel, processed_row_data)
                success_count += 1
            except Exception as e:
                # Catch any exceptions during database interaction or service logic for a specific row
                error_count += 1
                row_error_details.append({
                    "row_number": row_num,
                    "data": processed_row_data,
                    "error_description": f"Processing Error: {str(e)}"
                })
                db_session.rollback() # Rollback any changes made by the service for this specific row
                                      # to ensure atomicity per row if the service commits per row,
                                      # or to clear the session if the service adds to session.

        # Update the ingestion log with final status and counts (FR37, FR38)
        ingestion_log.status = "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS"
        ingestion_log.success_count = success_count
        ingestion_log.error_count = error_count
        if row_error_details:
            # Store detailed errors as a JSON string in the database (assuming JSONB column)
            ingestion_log.error_details_json = json.dumps(row_error_details)

        db_session.commit() # Commit the final status and counts of the ingestion log

        return {
            "status": "success",
            "log_id": log_id,
            "success_count": success_count,
            "error_count": error_count
        }

    except Exception as e:
        # Handle critical errors that prevent full file processing (e.g., invalid CSV format, decoding errors)
        db_session.rollback() # Rollback any pending changes if a critical error occurred
        # Update the ingestion log to reflect the overall failure
        ingestion_log.status = "FAILED"
        ingestion_log.error_description = f"File processing failed: {str(e)}"
        ingestion_log.success_count = success_count # Capture counts up to the point of failure
        ingestion_log.error_count = error_count # Capture counts up to the point of failure
        if row_error_details:
            ingestion_log.error_details_json = json.dumps(row_error_details)
        db_session.commit() # Commit the failed status

        return {
            "status": "error",
            "log_id": log_id,
            "success_count": success_count,
            "error_count": error_count,
            "message": f"File processing failed: {str(e)}"
        }

def generate_error_csv_content(error_details: list) -> io.StringIO:
    """
    Generates CSV file content from a list of error details.
    This function is used to prepare the "Error Excel file" (FR34, FR38) for download.

    Args:
        error_details (list): A list of dictionaries, where each dictionary contains
                              'row_number', 'error_description', and 'data' (the original row data).

    Returns:
        io.StringIO: An in-memory file-like object containing the CSV content.
    """
    if not error_details:
        return io.StringIO("") # Return empty CSV if no errors

    # Determine all unique column headers from the 'data' field across all error entries.
    all_data_keys = set()
    for detail in error_details:
        all_data_keys.update(detail.get("data", {}).keys())

    # Define the order of columns for the output CSV.
    # 'row_number' and 'error_description' are always first, followed by sorted data keys.
    sorted_headers = ["row_number", "error_description"] + sorted(list(all_data_keys))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=sorted_headers)

    writer.writeheader() # Write the header row to the CSV

    # Write each error detail as a row in the CSV
    for detail in error_details:
        row_output = {}
        row_output["row_number"] = detail.get("row_number")
        row_output["error_description"] = detail.get("error_description")
        # Populate data fields, using empty string for missing keys to avoid KeyError
        for header in all_data_keys:
            row_output[header] = detail.get("data", {}).get(header, "")
        writer.writerow(row_output)

    output.seek(0) # Reset stream position to the beginning for reading
    return output