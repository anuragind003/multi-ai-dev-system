from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime
import base64
import io
import csv

# Assume db is initialized and imported from a central location,
# e.g., from backend.database import db
# For this example, we'll mock db operations.
# In a real application, you would have SQLAlchemy models or direct psycopg2 calls.

ingestion_bp = Blueprint('ingestion_routes', __name__)

# Mock database operations for demonstration purposes
# In a real app, these would interact with PostgreSQL via SQLAlchemy or psycopg2
def mock_db_insert(table_name, data):
    """Simulates inserting data into a table."""
    print(f"Mock DB: Inserting into {table_name}: {data}")
    # In a real scenario, this would be db.session.add(Model(**data)) and db.session.commit()
    return True

def mock_db_update(table_name, identifier, data):
    """Simulates updating data in a table."""
    print(f"Mock DB: Updating {table_name} for {identifier}: {data}")
    # In a real scenario, this would be Model.query.filter_by(...).update(...)
    return True

def mock_db_log_ingestion(log_id, file_name, status, error_description=None):
    """Simulates logging ingestion status."""
    log_data = {
        "log_id": log_id,
        "file_name": file_name,
        "upload_timestamp": datetime.now().isoformat(),
        "status": status,
        "error_description": error_description
    }
    print(f"Mock DB: Logging ingestion: {log_data}")
    return True


@ingestion_bp.route('/api/leads', methods=['POST'])
def receive_leads():
    """
    Receives real-time lead generation data from Insta/E-aggregators
    and inserts into CDP.
    FR7, FR11, FR12
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    required_fields = [
        "mobile_number", "pan_number", "aadhaar_number",
        "loan_type", "source_channel"
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    customer_id = str(uuid.uuid4())
    try:
        customer_data = {
            "customer_id": customer_id,
            "mobile_number": data.get("mobile_number"),
            "pan_number": data.get("pan_number"),
            "aadhaar_number": data.get("aadhaar_number"),
            # UCID and loan_application_number might be added later
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        # In a real app, perform deduplication logic here (FR3, FR4, FR5, FR6)
        # before inserting or updating.
        mock_db_insert("customers", customer_data)

        # Potentially insert an initial offer or event based on lead
        # For simplicity, we'll just return customer_id for now.

        return jsonify({
            "status": "success",
            "customer_id": customer_id
        }), 201
    except Exception as e:
        print(f"Error processing lead: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@ingestion_bp.route('/api/eligibility', methods=['POST'])
def update_eligibility():
    """
    Receives real-time eligibility data from Insta/E-aggregators
    and updates customer/offer data.
    FR7, FR11, FR12
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    required_fields = [
        "customer_id", "offer_id", "eligibility_status", "loan_amount"
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        # In a real app, fetch the offer/customer and update.
        # This might involve updating offer_status, loan_amount, etc.
        offer_update_data = {
            "eligibility_status": data["eligibility_status"],
            "loan_amount": data["loan_amount"],
            "updated_at": datetime.now()
        }
        mock_db_update("offers", data["offer_id"], offer_update_data)

        return jsonify({
            "status": "success",
            "message": "Eligibility updated"
        }), 200
    except Exception as e:
        print(f"Error updating eligibility: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@ingestion_bp.route('/api/status-updates', methods=['POST'])
def update_status():
    """
    Receives real-time application status updates from Insta/E-aggregators
    or LOS.
    FR11, FR12, FR22, FR25, FR26
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    required_fields = [
        "loan_application_number", "customer_id", "current_stage",
        "status_timestamp"
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "customer_id": data["customer_id"],
            "event_type": data["current_stage"],  # Map stage to event type
            "event_source": data.get("source", "LOS/E-aggregator"),
            "event_timestamp": datetime.fromisoformat(
                data["status_timestamp"]
            ),
            "event_details": {
                "loan_application_number": data["loan_application_number"]
            },
            "created_at": datetime.now()
        }
        mock_db_insert("events", event_data)

        # FR14: Prevent modification of customer offers with started loan journey
        # This logic would typically be in a service layer, not directly here.
        # FR43: Mark offers as expired for journey started customers whose LAN validity is over.
        # This would be a scheduled job, not real-time API.

        return jsonify({
            "status": "success",
            "message": "Status updated"
        }), 200
    except ValueError as ve:
        return jsonify({"error": "Invalid timestamp format",
                        "details": str(ve)}), 400
    except Exception as e:
        print(f"Error updating status: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@ingestion_bp.route('/admin/customer-data/upload', methods=['POST'])
def upload_customer_data():
    """
    Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans)
    via Admin Portal.
    FR35, FR36, FR37, FR38
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    required_fields = ["file_content", "file_name", "loan_type"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    file_content_b64 = data["file_content"]
    file_name = data["file_name"]
    loan_type = data["loan_type"]
    log_id = str(uuid.uuid4())

    success_count = 0
    error_count = 0
    errors = []

    try:
        decoded_content = base64.b64decode(file_content_b64).decode('utf-8')
        csv_file = io.StringIO(decoded_content)
        csv_reader = csv.DictReader(csv_file)

        # Basic validation for expected headers (example)
        expected_headers = [
            "mobile_number", "pan_number", "aadhaar_number", "ucid_number"
        ]
        if not all(header in csv_reader.fieldnames
                   for header in expected_headers):
            error_msg = (f"CSV file missing one or more required headers: "
                         f"{', '.join(expected_headers)}")
            mock_db_log_ingestion(log_id, file_name, "FAILED", error_msg)
            return jsonify({
                "status": "error",
                "log_id": log_id,
                "message": error_msg
            }), 400

        for i, row in enumerate(csv_reader):
            row_num = i + 2  # Account for header row
            try:
                # FR1: Basic column-level validation
                # Example: Check if mobile_number is present and numeric
                mobile_number = row.get("mobile_number")
                if not mobile_number or not mobile_number.isdigit():
                    raise ValueError("Invalid or missing mobile_number")

                # Generate customer_id for each potential new customer
                customer_id = str(uuid.uuid4())

                customer_data = {
                    "customer_id": customer_id,
                    "mobile_number": mobile_number,
                    "pan_number": row.get("pan_number"),
                    "aadhaar_number": row.get("aadhaar_number"),
                    "ucid_number": row.get("ucid_number"),
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }

                # In a real application:
                # 1. Perform deduplication (FR3, FR4, FR5, FR6)
                #    - Check if customer already exists based on identifiers.
                #    - If exists, update existing profile; otherwise, insert new.
                # 2. Insert/Update customer data in 'customers' table.
                # 3. Generate leads (FR36) - this implies creating an offer
                #    or marking the customer as a prospect.
                #    This would involve inserting into the 'offers' table.

                mock_db_insert("customers", customer_data)
                success_count += 1

            except Exception as row_e:
                error_count += 1
                errors.append({
                    "row_number": row_num,
                    "data": row,
                    "error_desc": str(row_e)
                })

        status = "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS"
        error_description = (
            "Some rows failed processing." if error_count > 0 else None
        )
        mock_db_log_ingestion(log_id, file_name, status, error_description)

        # In a real app, you might save the errors list to a file
        # or a dedicated error log table for download (FR34, FR38).

        return jsonify({
            "status": status,
            "log_id": log_id,
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors if error_count > 0 else []
        }), 200

    except base64.binascii.Error:
        error_msg = "Invalid base64 encoding for file content."
        mock_db_log_ingestion(log_id, file_name, "FAILED", error_msg)
        return jsonify({
            "status": "error",
            "log_id": log_id,
            "message": error_msg
        }), 400
    except Exception as e:
        error_msg = f"Failed to process file: {str(e)}"
        mock_db_log_ingestion(log_id, file_name, "FAILED", error_msg)
        print(f"Error during file upload: {e}")
        return jsonify({
            "status": "error",
            "log_id": log_id,
            "message": error_msg
        }), 500