import base64
import io
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import pandas as pd

# Assuming db is initialized in app/__init__.py and models are defined in app.models
from app import db
from app.models import Customer, DataIngestionLog, Offer

# Define the blueprint for admin routes
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# --- Helper/Service functions (simplified for this file, would typically be in app.services) ---

def process_customer_upload_file(file_content_bytes: bytes, file_type: str, uploaded_by: str) -> dict:
    """
    Processes the uploaded customer details file.
    This function simulates the complex logic of validation, deduplication,
    lead generation, and tracking success/failure.

    Args:
        file_content_bytes: The raw bytes of the uploaded file.
        file_type: The type of file being uploaded (e.g., 'Prospect', 'TW Loyalty').
        uploaded_by: The user who initiated the upload.

    Returns:
        A dictionary containing the processing status, message, and log_id.
    """
    logger = current_app.logger
    log_id = uuid.uuid4()
    # Determine file extension for logging purposes, assuming CSV for simplicity
    # In a real scenario, you might infer from content or expect client to send extension
    file_extension = '.csv' # Default assumption
    if file_type.lower() in ['prospect', 'tw loyalty', 'topup', 'employee loans']:
        # For simplicity, we assume CSV. If Excel is expected, pd.read_excel would be used.
        pass
    else:
        # For now, we'll proceed with CSV parsing, but a more robust check might be needed.
        logger.warning(f"Unknown file type '{file_type}' received. Attempting to parse as CSV.")

    file_name = f"{file_type}_upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{file_extension}"

    # Create an initial log entry
    log_entry = DataIngestionLog(
        log_id=log_id,
        file_name=file_name,
        upload_timestamp=datetime.utcnow(),
        status='PENDING',
        uploaded_by=uploaded_by
    )
    db.session.add(log_entry)
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Failed to create initial DataIngestionLog entry for {file_name}: {e}")
        db.session.rollback()
        return {"status": "error", "message": "Failed to log upload initiation.", "log_id": str(log_id)}

    try:
        # Read the file content into a pandas DataFrame
        df = pd.read_csv(io.BytesIO(file_content_bytes))

        if df.empty:
            log_entry.status = 'FAILED'
            log_entry.error_details = 'Uploaded file is empty or contains no data rows.'
            db.session.commit()
            return {"status": "error", "message": "Uploaded file is empty or contains no data rows.", "log_id": str(log_id)}

        # FR1: Basic column-level validation
        # Example required columns. Actual columns would depend on file_type.
        required_columns = ['mobile_number', 'pan']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            log_entry.status = 'FAILED'
            log_entry.error_details = f"Missing required columns: {', '.join(missing_cols)}"
            db.session.commit()
            return {"status": "error", "message": log_entry.error_details, "log_id": str(log_id)}

        success_count = 0
        failed_records = []

        # Simulate row-by-row processing, validation, deduplication, and lead generation
        for index, row in df.iterrows():
            try:
                # Basic data cleaning and type conversion
                mobile_number = str(row.get('mobile_number')).strip() if pd.notna(row.get('mobile_number')) else None
                pan = str(row.get('pan')).strip() if pd.notna(row.get('pan')) else None
                aadhaar_ref_number = str(row.get('aadhaar_ref_number')).strip() if pd.notna(row.get('aadhaar_ref_number')) else None
                ucid = str(row.get('ucid')).strip() if pd.notna(row.get('ucid')) else None
                previous_loan_app_number = str(row.get('previous_loan_app_number')).strip() if pd.notna(row.get('previous_loan_app_number')) else None
                offer_type = str(row.get('offer_type')).strip() if pd.notna(row.get('offer_type')) else 'Fresh' # Default or infer

                if not mobile_number:
                    raise ValueError("Mobile number is a mandatory field.")

                # FR2, FR3, FR4, FR5: Deduplication logic (simplified placeholder)
                # Attempt to find an existing customer based on primary identifiers
                customer = db.session.query(Customer).filter(
                    (Customer.mobile_number == mobile_number) |
                    (Customer.pan == pan if pan else False) |
                    (Customer.aadhaar_ref_number == aadhaar_ref_number if aadhaar_ref_number else False) |
                    (Customer.ucid == ucid if ucid else False) |
                    (Customer.previous_loan_app_number == previous_loan_app_number if previous_loan_app_number else False)
                ).first()

                if not customer:
                    # Create new customer if no match found
                    customer = Customer(
                        mobile_number=mobile_number,
                        pan=pan,
                        aadhaar_ref_number=aadhaar_ref_number,
                        ucid=ucid,
                        previous_loan_app_number=previous_loan_app_number,
                        customer_segment='C1' # Default segment, could be derived from file_type or data
                    )
                    db.session.add(customer)
                    db.session.flush() # Assigns customer_id before commit for offer creation

                # FR30: Generate a lead (represented by creating/updating an Offer)
                # This is a simplified lead generation. Real logic would be more complex,
                # potentially checking for existing active offers before creating a new one.
                offer = Offer(
                    customer_id=customer.customer_id,
                    offer_type=offer_type,
                    offer_status='Active', # FR15
                    offer_start_date=datetime.utcnow().date(),
                    offer_end_date=datetime.utcnow().date() + timedelta(days=30), # Example expiry (FR37)
                    propensity_flag='default', # FR17
                    attribution_channel='Admin Upload' # FR20
                )
                db.session.add(offer)
                db.session.commit() # Commit each row for atomicity in this simplified example
                success_count += 1

            except (ValueError, IntegrityError, SQLAlchemyError) as e:
                db.session.rollback() # Rollback current row's transaction if error occurs
                error_desc = str(e)
                failed_records.append({
                    'row_index': index,
                    'data': row.to_dict(),
                    'error_desc': error_desc
                })
                logger.warning(f"Failed to process row {index} for {file_name}: {error_desc}")
                continue # Continue to next row

        # Update the log entry based on processing results
        if success_count == len(df):
            log_entry.status = 'SUCCESS'
            log_entry.error_details = None
        elif success_count > 0:
            log_entry.status = 'PARTIAL'
            log_entry.error_details = f"Processed {success_count} records successfully, {len(failed_records)} failed."
            # For FR32 (Error Excel file), the failed_records would need to be stored
            # persistently (e.g., in a JSONB column in DataIngestionLog or a separate table)
            # and retrieved by the /api/reports/error-data endpoint.
        else:
            log_entry.status = 'FAILED'
            log_entry.error_details = f"All {len(failed_records)} records failed. First error: {failed_records[0]['error_desc'] if failed_records else 'Unknown'}"

        db.session.commit() # Commit final log status

        if log_entry.status == 'SUCCESS':
            message = "File uploaded and processed successfully."
        elif log_entry.status == 'PARTIAL':
            message = f"File processed with some errors. {success_count} records successful, {len(failed_records)} failed."
        else:
            message = f"File upload failed: {log_entry.error_details}"

        return {"status": log_entry.status.lower(), "message": message, "log_id": str(log_id)}

    except pd.errors.EmptyDataError:
        log_entry.status = 'FAILED'
        log_entry.error_details = 'Uploaded file is empty or malformed (no data found).'
        db.session.commit()
        logger.error(f"EmptyDataError during file processing for log_id {log_id}: {log_entry.error_details}")
        return {"status": "error", "message": "Uploaded file is empty or malformed.", "log_id": str(log_id)}
    except pd.errors.ParserError as e:
        log_entry.status = 'FAILED'
        log_entry.error_details = f'Error parsing file content: {e}'
        db.session.commit()
        logger.error(f"ParserError during file processing for log_id {log_id}: {e}")
        return {"status": "error", "message": f"Error parsing file content. Please check format: {e}", "log_id": str(log_id)}
    except ValueError as e:
        log_entry.status = 'FAILED'
        log_entry.error_details = f'File processing error: {e}'
        db.session.commit()
        logger.error(f"ValueError during file processing for log_id {log_id}: {e}")
        return {"status": "error", "message": f"File processing error: {e}", "log_id": str(log_id)}
    except Exception as e:
        db.session.rollback() # Ensure rollback on unexpected errors
        log_entry.status = 'FAILED'
        log_entry.error_details = f'An unexpected error occurred during file processing: {e}'
        db.session.commit()
        logger.exception(f"Unexpected error during file processing for log_id {log_id}: {e}")
        return {"status": "error", "message": "An unexpected internal error occurred during file processing.", "log_id": str(log_id)}


@admin_bp.route('/upload/customer-details', methods=['POST'])
def upload_customer_details():
    """
    API endpoint for uploading customer details files (Prospect, TW Loyalty, Topup, Employee loans).
    FR29: The Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.
    FR30: The Admin Portal shall generate a lead for customers in the system upon successful file upload.
    FR31: The Admin Portal shall generate a success file upon successful upload of all data.
    FR32: The Admin Portal shall generate an error file with an 'Error Desc' column for failed uploads.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    file_type = data.get('file_type')
    file_content_base64 = data.get('file_content_base64')
    uploaded_by = data.get('uploaded_by')

    if not all([file_type, file_content_base64, uploaded_by]):
        return jsonify({"status": "error", "message": "Missing required fields: 'file_type', 'file_content_base64', 'uploaded_by'"}), 400

    try:
        file_content_bytes = base64.b64decode(file_content_base64)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid base64 encoded file content: {e}"}), 400

    # Process the file. In a production system, for large files, this might be
    # offloaded to a background task queue (e.g., Celery) to avoid blocking the API.
    # For this exercise, we call it directly.
    result = process_customer_upload_file(file_content_bytes, file_type, uploaded_by)

    status_code = 200
    if result['status'] == 'error':
        # Use 400 for client-side errors (e.g., bad file format, missing data)
        # Use 500 for server-side errors (e.g., database connection issues, unexpected exceptions)
        if "internal error" in result['message'].lower() or "unexpected error" in result['message'].lower() or "failed to log upload initiation" in result['message'].lower():
            status_code = 500
        else:
            status_code = 400
    elif result['status'] == 'partial':
        status_code = 202 # Accepted, but with issues

    return jsonify(result), status_code