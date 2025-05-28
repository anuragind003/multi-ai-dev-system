import base64
import io
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

# --- Mocking for standalone execution/demonstration ---
# In a real Flask app, `db` would be initialized via Flask-SQLAlchemy
# and models would be imported from `app.models`.
# For this exercise, we'll use mock objects to simulate database interaction
# and a placeholder service for complex business logic.

class MockDB:
    """A mock database object to simulate SQLAlchemy session behavior."""
    def __init__(self):
        self.session = self # Mock session as self

    def add(self, instance):
        """Simulates adding an instance to the session."""
        # In a real app, this would add to the SQLAlchemy session
        pass

    def commit(self):
        """Simulates committing the transaction."""
        # In a real app, this would commit the SQLAlchemy transaction
        pass

    def rollback(self):
        """Simulates rolling back the transaction."""
        # In a real app, this would rollback the SQLAlchemy transaction
        pass

    def close(self):
        """Simulates closing the session."""
        # In a real app, this would close the SQLAlchemy session
        pass

db = MockDB()

class DataIngestionLog:
    """A mock model for the data_ingestion_logs table."""
    def __init__(self, log_id, file_name, upload_timestamp, status, error_details, uploaded_by):
        self.log_id = log_id
        self.file_name = file_name
        self.upload_timestamp = upload_timestamp
        self.status = status
        self.error_details = error_details
        self.uploaded_by = uploaded_by

    def __repr__(self):
        return f"<DataIngestionLog {self.log_id} - {self.status}>"

# Placeholder for a service that would handle the actual file processing
class CustomerDataService:
    """
    A placeholder service for processing customer data uploads.
    In a real application, this would contain the complex business logic
    for parsing, validation, deduplication, and lead generation.
    """
    def process_customer_upload(self, file_type: str, file_content_bytes: bytes, uploaded_by: str) -> dict:
        """
        Simulates the processing of an uploaded customer file.

        This would typically involve:
        1. Reading the file content (e.g., CSV, Excel) using libraries like pandas.
        2. Performing column-level validation (FR1).
        3. Applying deduplication logic (FR3, FR4, FR5).
        4. Inserting/updating customer and offer data in the database.
        5. Generating leads (FR30).
        6. Generating success/error files (FR31, FR32).

        For this example, we'll simulate success, partial success, or failure.
        """
        current_app.logger.info(f"CustomerDataService: Processing upload for file_type={file_type}, uploaded_by={uploaded_by}")
        
        # Simulate processing time and outcome
        import random
        if random.random() < 0.8: # 80% chance of success
            # Simulate successful processing
            return {
                "status": "SUCCESS",
                "message": "File processed successfully. Leads generated.",
                "success_records": random.randint(50, 200),
                "failed_records": 0,
                "error_file_path": None # No error file needed for full success
            }
        else:
            # Simulate failure or partial success
            total_records = random.randint(50, 200)
            failed_count = random.randint(1, total_records // 2)
            success_count = total_records - failed_count
            
            status = "PARTIAL_SUCCESS" if success_count > 0 else "FAILED"
            message = f"File processing completed with {failed_count} errors. Please download the error file for details."
            
            return {
                "status": status,
                "message": message,
                "success_records": success_count,
                "failed_records": failed_count,
                "error_file_path": f"/tmp/error_file_{uuid.uuid4()}.xlsx" # Example path for error file
            }

customer_data_service = CustomerDataService()
# --- End Mocking ---


admin_bp = Blueprint('admin_routes', __name__, url_prefix='/api/admin')

@admin_bp.route('/upload/customer-details', methods=['POST'])
def upload_customer_details():
    """
    API endpoint for uploading customer details files (Prospect, TW Loyalty, Topup, Employee loans)
    for lead generation via Admin Portal.
    (FR29: Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.)
    (FR30: Admin Portal shall generate a lead for customers in the system upon successful file upload.)
    (FR31: Admin Portal shall generate a success file upon successful upload of all data.)
    (FR32: Admin Portal shall generate an error file with an 'Error Desc' column for failed uploads.)
    """
    data = request.get_json()

    if not data:
        current_app.logger.warning("No input data provided for customer details upload.")
        return jsonify({"status": "error", "message": "No input data provided"}), 400

    file_type = data.get('file_type')
    file_content_base64 = data.get('file_content_base64')
    uploaded_by = data.get('uploaded_by', 'anonymous') # Default to 'anonymous' if not provided

    if not all([file_type, file_content_base64]):
        current_app.logger.warning(f"Missing file_type or file_content_base64 for upload by {uploaded_by}.")
        return jsonify({"status": "error", "message": "Missing file_type or file_content_base64"}), 400

    log_id = str(uuid.uuid4())
    # In a real scenario, the file name might be derived from the original upload or a standardized format
    file_name = f"{file_type}_upload_{log_id}.bin" # Using .bin as it's base64 decoded raw bytes

    try:
        file_content_bytes = base64.b64decode(file_content_base64)
    except Exception as e:
        current_app.logger.error(f"Base64 decoding error for log_id {log_id}, uploaded by {uploaded_by}: {e}")
        return jsonify({"status": "error", "message": "Invalid base64 encoded file content"}), 400

    # Log the start of the ingestion process
    ingestion_log = DataIngestionLog(
        log_id=log_id,
        file_name=file_name,
        upload_timestamp=datetime.now(),
        status="INITIATED", # Initial status before processing begins
        error_details=None,
        uploaded_by=uploaded_by
    )
    try:
        db.add(ingestion_log)
        db.commit()
        current_app.logger.info(f"Logged initiation of file upload for log_id: {log_id}")
    except SQLAlchemyError as e:
        db.rollback()
        current_app.logger.error(f"Database error logging ingestion start for {log_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to log upload initiation"}), 500

    try:
        # Call the service to process the file content.
        # In a production environment, for large files or long processing times,
        # this call should ideally be asynchronous (e.g., using Celery or RQ)
        # to prevent API timeouts and improve responsiveness.
        processing_result = customer_data_service.process_customer_upload(
            file_type, file_content_bytes, uploaded_by
        )

        # Update the log based on the processing result
        ingestion_log.status = processing_result.get("status")
        ingestion_log.error_details = processing_result.get("message") if processing_result.get("status") in ["FAILED", "PARTIAL_SUCCESS"] else None
        db.add(ingestion_log)
        db.commit()
        current_app.logger.info(f"Updated log_id {log_id} with status: {ingestion_log.status}")

        response_status_code = 200
        if processing_result.get("status") == "FAILED":
            response_status_code = 400 # Bad request if processing completely failed due to data issues
        elif processing_result.get("status") == "PARTIAL_SUCCESS":
            response_status_code = 202 # Accepted, but with partial success (processing ongoing or completed with errors)

        return jsonify({
            "status": processing_result.get("status"),
            "message": processing_result.get("message", "File uploaded and processed."),
            "log_id": log_id,
            "success_records": processing_result.get("success_records"),
            "failed_records": processing_result.get("failed_records"),
            "error_file_path": processing_result.get("error_file_path") # Will be None for full success
        }), response_status_code

    except Exception as e:
        db.rollback() # Ensure rollback if any error occurs during processing
        current_app.logger.error(f"Unhandled error during customer upload processing for log_id {log_id}: {e}", exc_info=True)
        
        # Attempt to update log status to FAILED if an unhandled exception occurs
        ingestion_log.status = "FAILED"
        ingestion_log.error_details = f"Internal server error during processing: {str(e)}"
        try:
            db.add(ingestion_log)
            db.commit()
            current_app.logger.info(f"Updated log_id {log_id} to FAILED due to unhandled exception.")
        except SQLAlchemyError as log_e:
            current_app.logger.error(f"Failed to update log status after processing error for {log_id}: {log_e}", exc_info=True)
            db.rollback() # Rollback the log update if it fails

        return jsonify({"status": "error", "message": "An internal server error occurred during file processing."}), 500