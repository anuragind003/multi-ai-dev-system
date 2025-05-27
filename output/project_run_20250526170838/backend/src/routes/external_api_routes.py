from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime
import logging

# Configure logging for the module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

external_api_bp = Blueprint('external_api', __name__)

# --- Mock Service Layer ---
# In a real application, these services would interact with the PostgreSQL database
# using an ORM like SQLAlchemy or a direct database connector like psycopg2.
# For the purpose of this file, we're using mock services to demonstrate the API logic.
# These mocks simulate success and basic ID generation.

class MockCustomerService:
    def create_lead(self, data):
        """
        Simulates creating a lead. In a real scenario, this would involve:
        1. Data validation (FR1, NFR3)
        2. Deduplication logic (FR3, FR4, FR5, FR6)
        3. Inserting/updating customer data in the 'customers' table.
        4. Potentially creating initial offer records.
        """
        customer_id = str(uuid.uuid4())
        logger.info(f"Mock: Creating lead for mobile {data.get('mobile_number')} with customer_id {customer_id}")
        # Simulate successful creation
        return {"status": "success", "customer_id": customer_id}

class MockOfferService:
    def update_eligibility(self, customer_id, offer_id, eligibility_status, loan_amount):
        """
        Simulates updating offer eligibility. In a real scenario, this would involve:
        1. Data validation.
        2. Updating the 'offers' table for the given customer_id and offer_id.
        """
        logger.info(f"Mock: Updating eligibility for customer {customer_id}, offer {offer_id} to {eligibility_status} with amount {loan_amount}")
        # Simulate successful update
        return {"status": "success", "message": "Eligibility updated"}

class MockEventService:
    def record_application_status(self, loan_application_number, customer_id, current_stage, status_timestamp):
        """
        Simulates recording an application status event. In a real scenario, this would involve:
        1. Data validation.
        2. Inserting event data into the 'events' table (FR22, FR26).
        """
        event_id = str(uuid.uuid4())
        logger.info(f"Mock: Recording application status for LAN {loan_application_number}, customer {customer_id}, stage {current_stage} at {status_timestamp}")
        # Simulate successful recording
        return {"status": "success", "event_id": event_id, "message": "Status updated"}

# Instantiate mock services
customer_service = MockCustomerService()
offer_service = MockOfferService()
event_service = MockEventService()

# --- API Endpoints ---

@external_api_bp.route('/api/leads', methods=['POST'])
def receive_leads():
    """
    API endpoint to receive real-time lead generation data from Insta/E-aggregators.
    This data is then inserted into the CDP database.
    (Functional Requirements: FR7, FR11, FR12)
    """
    data = request.json
    if not data:
        logger.warning("API /api/leads: No JSON data received.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    required_fields = ["mobile_number", "pan_number", "aadhaar_number", "loan_type", "source_channel"]
    for field in required_fields:
        if field not in data or not data[field]:
            logger.warning(f"API /api/leads: Missing or empty required field: {field}")
            return jsonify({"status": "error", "message": f"Missing or empty required field: {field}"}), 400

    try:
        # Call the service layer to process the lead data
        result = customer_service.create_lead(data)
        if result.get("status") == "success":
            logger.info(f"API /api/leads: Successfully processed lead for mobile {data.get('mobile_number')}")
            return jsonify(result), 200
        else:
            logger.error(f"API /api/leads: Failed to process lead: {result.get('message', 'Unknown error')}")
            return jsonify({"status": "error", "message": result.get("message", "Failed to process lead")}), 500
    except Exception as e:
        logger.exception(f"API /api/leads: An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@external_api_bp.route('/api/eligibility', methods=['POST'])
def receive_eligibility():
    """
    API endpoint to receive real-time eligibility data from Insta/E-aggregators.
    This data is used to update customer and offer information in the CDP.
    (Functional Requirements: FR7, FR11, FR12)
    """
    data = request.json
    if not data:
        logger.warning("API /api/eligibility: No JSON data received.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    required_fields = ["customer_id", "offer_id", "eligibility_status", "loan_amount"]
    for field in required_fields:
        # loan_amount can be 0.0, so check for None, not just falsy
        if field not in data or data[field] is None:
            logger.warning(f"API /api/eligibility: Missing required field: {field}")
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400

    try:
        # Call the service layer to update eligibility
        result = offer_service.update_eligibility(
            data["customer_id"],
            data["offer_id"],
            data["eligibility_status"],
            data["loan_amount"]
        )
        if result.get("status") == "success":
            logger.info(f"API /api/eligibility: Successfully updated eligibility for customer {data['customer_id']}")
            return jsonify(result), 200
        else:
            logger.error(f"API /api/eligibility: Failed to update eligibility: {result.get('message', 'Unknown error')}")
            return jsonify({"status": "error", "message": result.get("message", "Failed to update eligibility")}), 500
    except Exception as e:
        logger.exception(f"API /api/eligibility: An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@external_api_bp.route('/api/status-updates', methods=['POST'])
def receive_status_updates():
    """
    API endpoint to receive real-time application status updates from Insta/E-aggregators or LOS.
    This data is stored as events in the CDP.
    (Functional Requirements: FR11, FR12, FR26)
    """
    data = request.json
    if not data:
        logger.warning("API /api/status-updates: No JSON data received.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    required_fields = ["loan_application_number", "customer_id", "current_stage", "status_timestamp"]
    for field in required_fields:
        if field not in data or not data[field]:
            logger.warning(f"API /api/status-updates: Missing or empty required field: {field}")
            return jsonify({"status": "error", "message": f"Missing or empty required field: {field}"}), 400

    try:
        # Validate and parse the timestamp
        status_timestamp_str = data["status_timestamp"]
        try:
            # Handle common ISO 8601 formats, including 'Z' for UTC
            status_timestamp = datetime.fromisoformat(status_timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"API /api/status-updates: Invalid status_timestamp format: {status_timestamp_str}")
            return jsonify({"status": "error", "message": "Invalid status_timestamp format. Expected ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ)."}), 400

        # Call the service layer to record the application status event
        result = event_service.record_application_status(
            data["loan_application_number"],
            data["customer_id"],
            data["current_stage"],
            status_timestamp
        )
        if result.get("status") == "success":
            logger.info(f"API /api/status-updates: Successfully recorded status for LAN {data['loan_application_number']}")
            return jsonify(result), 200
        else:
            logger.error(f"API /api/status-updates: Failed to record status: {result.get('message', 'Unknown error')}")
            return jsonify({"status": "error", "message": result.get("message", "Failed to record status")}), 500
    except Exception as e:
        logger.exception(f"API /api/status-updates: An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500