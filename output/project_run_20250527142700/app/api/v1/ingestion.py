from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent # Assuming these models are defined
from app.services.ingestion_service import IngestionService # Assuming this service exists and handles business logic

# Define the blueprint for API version 1 ingestion routes
ingestion_bp = Blueprint('ingestion_v1', __name__, url_prefix='/api/v1')

# Initialize the ingestion service. This service will contain the core business logic
# for processing incoming data, including validation, deduplication, and database interactions.
ingestion_service = IngestionService()

@ingestion_bp.route('/leads', methods=['POST'])
def create_lead():
    """
    API endpoint to receive real-time lead generation data from Insta/E-aggregators.
    This data is processed and inserted into the CDP database.

    Functional Requirements Addressed:
    - FR9: Receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation API).
    - FR10: Modify existing APIs to insert data into the CDP database instead of the MAS database.
    - FR1, FR2, FR3, FR4: Implies basic column-level validation and deduplication logic handled by the service.

    Request Body (JSON):
    {
        "mobile_number": "string",
        "pan": "string", (optional)
        "aadhaar_ref_number": "string", (optional)
        "ucid": "string", (optional)
        "previous_loan_app_number": "string", (optional)
        "loan_type": "string",
        "source_channel": "string",
        "application_id": "string" (optional)
    }

    Response (JSON):
    - Success (201 Created): {"status": "success", "message": "Lead processed successfully", "customer_id": "uuid"}
    - Error (400 Bad Request): {"status": "error", "message": "Missing required fields..."}
    - Error (409 Conflict): {"status": "error", "message": "Database integrity error, possibly duplicate entry."}
    - Error (500 Internal Server Error): {"status": "error", "message": "An unexpected error occurred."}
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("API /v1/leads: No JSON data received.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    # Basic validation for required fields at the API gateway level
    required_fields = ['mobile_number', 'loan_type', 'source_channel']
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        current_app.logger.warning(f"API /v1/leads: Missing required fields: {', '.join(missing)}. Received keys: {list(data.keys())}")
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        # Delegate the core business logic (validation, deduplication, DB insertion) to the service layer
        customer_id = ingestion_service.process_lead_data(data)
        current_app.logger.info(f"API /v1/leads: Lead processed successfully for customer_id: {customer_id}")
        return jsonify({
            "status": "success",
            "message": "Lead processed successfully",
            "customer_id": str(customer_id) # Convert UUID to string for JSON serialization
        }), 201
    except ValueError as e:
        # Catch validation errors from the service layer
        current_app.logger.error(f"API /v1/leads: Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except IntegrityError as e:
        # Handle database integrity errors (e.g., unique constraint violations)
        db.session.rollback() # Rollback the transaction on error
        current_app.logger.error(f"API /v1/leads: Database integrity error: {e}")
        return jsonify({"status": "error", "message": "Database integrity error, possibly duplicate entry or invalid reference."}), 409
    except SQLAlchemyError as e:
        # Handle other SQLAlchemy-related errors
        db.session.rollback()
        current_app.logger.error(f"API /v1/leads: Database error: {e}")
        return jsonify({"status": "error", "message": "Database error during lead processing."}), 500
    except Exception as e:
        # Catch any other unexpected errors
        db.session.rollback()
        current_app.logger.exception(f"API /v1/leads: An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@ingestion_bp.route('/eligibility', methods=['POST'])
def process_eligibility():
    """
    API endpoint to receive real-time eligibility check data from Insta/E-aggregators.
    This data is processed and recorded in the CDP database, potentially updating offers or logging events.

    Functional Requirements Addressed:
    - FR9: Receive real-time data from Insta or E-aggregators into CDP via Open APIs (Eligibility API).
    - FR10: Modify existing APIs to insert data into the CDP database instead of the MAS database.

    Request Body (JSON):
    {
        "mobile_number": "string",
        "loan_application_number": "string",
        "eligibility_status": "string",
        "offer_id": "string" (optional, if updating an existing offer)
    }

    Response (JSON):
    - Success (200 OK): {"status": "success", "message": "Eligibility data processed"}
    - Error (400 Bad Request): {"status": "error", "message": "Missing required fields..."}
    - Error (500 Internal Server Error): {"status": "error", "message": "An unexpected error occurred."}
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("API /v1/eligibility: No JSON data received.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    required_fields = ['mobile_number', 'loan_application_number', 'eligibility_status']
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        current_app.logger.warning(f"API /v1/eligibility: Missing required fields: {', '.join(missing)}. Received keys: {list(data.keys())}")
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        ingestion_service.process_eligibility_data(data)
        current_app.logger.info(f"API /v1/eligibility: Eligibility data processed for LAN: {data.get('loan_application_number')}")
        return jsonify({
            "status": "success",
            "message": "Eligibility data processed"
        }), 200
    except ValueError as e:
        current_app.logger.error(f"API /v1/eligibility: Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"API /v1/eligibility: Database error: {e}")
        return jsonify({"status": "error", "message": "Database error during eligibility processing."}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"API /v1/eligibility: An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@ingestion_bp.route('/status', methods=['POST'])
def process_status():
    """
    API endpoint to receive real-time loan application status updates from Insta/E-aggregators.
    This data is recorded as customer events in the CDP database.

    Functional Requirements Addressed:
    - FR9: Receive real-time data from Insta or E-aggregators into CDP via Open APIs (Status API).
    - FR10: Modify existing APIs to insert data into the CDP database instead of the MAS database.
    - FR22: Event data shall include application stages (login, bureau check, offer details, eKYC, Bank details, other details, e-sign) (from LOS).

    Request Body (JSON):
    {
        "loan_application_number": "string",
        "application_stage": "string", (e.g., "login", "bureau check", "eKYC")
        "status_details": "string", (optional, additional details)
        "event_timestamp": "string" (ISO 8601 format, e.g., "2023-10-27T10:30:00Z")
    }

    Response (JSON):
    - Success (200 OK): {"status": "success", "message": "Status updated"}
    - Error (400 Bad Request): {"status": "error", "message": "Missing required fields..."}
    - Error (500 Internal Server Error): {"status": "error", "message": "An unexpected error occurred."}
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("API /v1/status: No JSON data received.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    required_fields = ['loan_application_number', 'application_stage', 'event_timestamp']
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        current_app.logger.warning(f"API /v1/status: Missing required fields: {', '.join(missing)}. Received keys: {list(data.keys())}")
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

    try:
        ingestion_service.process_status_data(data)
        current_app.logger.info(f"API /v1/status: Status data processed for LAN: {data.get('loan_application_number')}, Stage: {data.get('application_stage')}")
        return jsonify({
            "status": "success",
            "message": "Status updated"
        }), 200
    except ValueError as e:
        current_app.logger.error(f"API /v1/status: Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"API /v1/status: Database error: {e}")
        return jsonify({"status": "error", "message": "Database error during status processing."}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"API /v1/status: An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500