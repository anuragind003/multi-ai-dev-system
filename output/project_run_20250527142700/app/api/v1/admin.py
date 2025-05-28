import base64
import io
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import pandas as pd

# Assuming db is initialized in app/__init__.py or app.py and models are defined in app.models
from app import db
from app.models import Customer, DataIngestionLog, Offer

# Define the blueprint for admin routes
# The instruction specifies `app/api/v1/admin.py`, so the URL prefix should reflect this.
admin_bp = Blueprint('admin_v1', __name__, url_prefix='/api/v1/admin')

# --- Helper/Service functions (simplified for this file, would typically be in app.services) ---

def process_customer_upload_file(file_content_bytes: bytes, file_type: str, uploaded_by: str) -> dict:
    """
    Processes the uploaded customer details file.
    This function simulates the complex logic of validation, deduplication,
    lead generation, and tracking success/failure.

    FR29: The Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.
    FR30: The Admin Portal shall generate a lead for customers in the system upon successful file upload.
    FR31: The Admin Portal shall generate a success file upon successful upload of all data.
    FR32: The Admin Portal shall generate an error file with an 'Error Desc' column for failed uploads.
    FR1: The system shall perform basic column-level validation when moving data from Offermart to CDP.
    """
    logger = current_app.logger
    log_id = uuid.uuid4()
    total_records = 0
    successful_records = 0
    failed_records = []
    error_details_list = []

    try:
        # Read the file content into a pandas DataFrame
        file_stream = io.BytesIO(file_content_bytes)
        if file_type.lower() == 'csv':
            df = pd.read_csv(file_stream)
        elif file_type.lower() in ['xls', 'xlsx']:
            df = pd.read_excel(file_stream)
        else:
            raise ValueError("Unsupported file type. Only CSV, XLS, XLSX are supported.")

        total_records = len(df)
        logger.info(f"Processing {total_records} records from uploaded file (Type: {file_type}, Log ID: {log_id})")

        # Basic validation: Check for essential columns
        # These columns are examples; actual required columns would come from BRD attachments.
        required_columns = ['mobile_number', 'pan', 'loan_type']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

        # Iterate through DataFrame rows and process each record
        for index, row in df.iterrows():
            record_errors = []
            # Basic column-level validation (FR1)
            mobile_number = str(row.get('mobile_number')).strip() if pd.notna(row.get('mobile_number')) else None
            pan = str(row.get('pan')).strip().upper() if pd.notna(row.get('pan')) else None
            loan_type = str(row.get('loan_type')).strip() if pd.notna(row.get('loan_type')) else None
            offer_amount = row.get('offer_amount') # Example field
            offer_end_date = row.get('offer_end_date') # Example field

            if not mobile_number or not pan or not loan_type:
                record_errors.append("Missing essential data (mobile_number, PAN, or loan_type).")

            # Further validation (e.g., PAN format, mobile number length)
            if pan and len(pan) != 10:
                record_errors.append("PAN must be 10 characters long.")
            if mobile_number and (not mobile_number.isdigit() or len(mobile_number) not in [10, 12]):
                record_errors.append("Mobile number must be 10 or 12 digits.")

            if record_errors:
                failed_records.append(row.to_dict())
                error_details_list.append({
                    "row_index": index,
                    "data": row.to_dict(),
                    "error_desc": "; ".join(record_errors)
                })
                continue # Skip to next record if basic validation fails

            try:
                # Deduplication logic (FR3, FR4, FR5) - Simplified:
                # Try to find an existing customer by mobile, PAN, or other unique identifiers
                customer = Customer.query.filter(
                    (Customer.mobile_number == mobile_number) |
                    (Customer.pan == pan)
                    # Add other identifiers like aadhaar_ref_number, ucid, previous_loan_app_number
                    # as per FR2 for a single profile view.
                ).first()

                if not customer:
                    # Create new customer if not found
                    customer = Customer(
                        mobile_number=mobile_number,
                        pan=pan,
                        # Populate other customer fields from the row if available
                        # e.g., aadhaar_ref_number=row.get('aadhaar_ref_number'),
                        # ucid=row.get('ucid'),
                        # previous_loan_app_number=row.get('previous_loan_app_number'),
                        customer_attributes=row.to_dict() # Store all row data as attributes for simplicity
                    )
                    db.session.add(customer)
                    db.session.flush() # To get customer_id for offer creation

                # Generate a lead (FR30) - Create an offer for the customer
                # This is a simplified lead generation. Real logic would involve more complex offer rules.
                # FR13: The system shall prevent modification of customer offers with started loan application journeys.
                # This check would be more complex, involving `loan_application_number` and `offer_status`.
                # For now, assume new offers can always be created or existing ones updated if not 'journey started'.

                offer_status = 'Active' # Default status for new leads
                offer_end_date_obj = None
                if pd.notna(offer_end_date):
                    try:
                        if isinstance(offer_end_date, datetime):
                            offer_end_date_obj = offer_end_date.date()
                        elif isinstance(offer_end_date, str):
                            offer_end_date_obj = pd.to_datetime(offer_end_date).date()
                        else:
                            logger.warning(f"Could not parse offer_end_date for row {index}: {offer_end_date}")
                    except Exception as e:
                        logger.warning(f"Error parsing offer_end_date '{offer_end_date}' for row {index}: {e}")

                new_offer = Offer(
                    customer_id=customer.customer_id,
                    offer_type=loan_type, # Using loan_type as offer_type for simplicity
                    offer_status=offer_status,
                    offer_start_date=datetime.now().date(),
                    offer_end_date=offer_end_date_obj,
                    # Populate other offer-related fields from the row if available
                    # e.g., propensity_flag=row.get('propensity_flag'),
                    # attribution_channel=row.get('channel')
                )
                db.session.add(new_offer)
                db.session.commit() # Commit each record for atomicity in case of large files, or batch commit later

                successful_records += 1

            except IntegrityError as e:
                db.session.rollback()
                error_msg = f"Database integrity error for record (mobile: {mobile_number}, PAN: {pan}): {e.orig}"
                logger.error(error_msg)
                failed_records.append(row.to_dict())
                error_details_list.append({
                    "row_index": index,
                    "data": row.to_dict(),
                    "error_desc": error_msg
                })
            except SQLAlchemyError as e:
                db.session.rollback()
                error_msg = f"Database error for record (mobile: {mobile_number}, PAN: {pan}): {e}"
                logger.error(error_msg)
                failed_records.append(row.to_dict())
                error_details_list.append({
                    "row_index": index,
                    "data": row.to_dict(),
                    "error_desc": error_msg
                })
            except Exception as e:
                db.session.rollback()
                error_msg = f"Unexpected error processing record (mobile: {mobile_number}, PAN: {pan}): {e}"
                logger.error(error_msg, exc_info=True) # Log traceback for unexpected errors
                failed_records.append(row.to_dict())
                error_details_list.append({
                    "row_index": index,
                    "data": row.to_dict(),
                    "error_desc": error_msg
                })

        # Log the ingestion status (FR31, FR32)
        status = "SUCCESS" if not failed_records else ("PARTIAL" if successful_records > 0 else "FAILED")
        error_summary = None
        if error_details_list:
            # Convert error_details_list to a JSON string for storage
            error_summary = pd.DataFrame(error_details_list).to_json(orient='records')

        ingestion_log = DataIngestionLog(
            log_id=log_id,
            file_name=f"customer_upload_{file_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            upload_timestamp=datetime.now(),
            status=status,
            error_details=error_summary,
            uploaded_by=uploaded_by
        )
        db.session.add(ingestion_log)
        db.session.commit()

        message = f"File processing completed. Total: {total_records}, Success: {successful_records}, Failed: {len(failed_records)}."
        if failed_records:
            message += " Some records failed. Check error log for details."
        logger.info(message)

        return {
            "status": "success" if status != "FAILED" else "error",
            "message": message,
            "log_id": str(log_id),
            "total_records": total_records,
            "successful_records": successful_records,
            "failed_records_count": len(failed_records)
        }

    except ValueError as e:
        db.session.rollback()
        logger.error(f"File processing error (Log ID: {log_id}): {e}")
        # Log this initial parsing error as well
        ingestion_log = DataIngestionLog(
            log_id=log_id,
            file_name=f"customer_upload_{file_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            upload_timestamp=datetime.now(),
            status="FAILED",
            error_details=f"Initial file parsing or validation error: {e}",
            uploaded_by=uploaded_by
        )
        db.session.add(ingestion_log)
        db.session.commit()
        return {
            "status": "error",
            "message": f"File processing failed: {e}",
            "log_id": str(log_id)
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"An unexpected error occurred during file processing (Log ID: {log_id}): {e}", exc_info=True)
        # Log this unexpected error
        ingestion_log = DataIngestionLog(
            log_id=log_id,
            file_name=f"customer_upload_{file_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            upload_timestamp=datetime.now(),
            status="FAILED",
            error_details=f"An unexpected internal server error occurred: {e}",
            uploaded_by=uploaded_by
        )
        db.session.add(ingestion_log)
        db.session.commit()
        return {
            "status": "error",
            "message": "An internal server error occurred during file processing.",
            "log_id": str(log_id)
        }


@admin_bp.route('/upload/customer-details', methods=['POST'])
def upload_customer_details():
    """
    API endpoint for uploading customer details file (Prospect, TW Loyalty, Topup, Employee loans).
    FR29: The Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    file_type = data.get('file_type')
    file_content_base64 = data.get('file_content_base64')
    uploaded_by = data.get('uploaded_by', 'Admin User') # Default to 'Admin User' if not provided

    if not file_type or not file_content_base64:
        return jsonify({"status": "error", "message": "Missing file_type or file_content_base64"}), 400

    try:
        file_content_bytes = base64.b64decode(file_content_base64)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid base64 encoding: {e}"}), 400

    # Call the helper function to process the file
    processing_result = process_customer_upload_file(file_content_bytes, file_type, uploaded_by)

    # Return the result from the processing function with appropriate HTTP status
    if processing_result.get("status") == "error":
        # If it's a client-side error (e.g., unsupported file type, missing columns), return 400
        # Otherwise, if it's a server-side processing error, return 500
        if "Unsupported file type" in processing_result.get("message", "") or \
           "Missing required columns" in processing_result.get("message", ""):
            return jsonify(processing_result), 400
        else:
            return jsonify(processing_result), 500
    else:
        return jsonify(processing_result), 200