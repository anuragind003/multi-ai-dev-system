from flask import Blueprint, request, jsonify
from backend.database import db
from backend.models import Customer, Offer, OfferHistory, Event
from backend.services.deduplication_service import process_e_aggregator_offer
from backend.services.validation_service import validate_e_aggregator_payload
import uuid
from datetime import datetime

# Define the Flask Blueprint for ingestion routes
ingestion_bp = Blueprint('ingestion', __name__, url_prefix='/ingest')

@ingestion_bp.route('/e-aggregator-data', methods=['POST'])
def ingest_e_aggregator_data():
    """
    API endpoint to receive real-time lead, eligibility, or status data from E-aggregators.
    Performs basic validation and delegates to a service for inserting/updating
    customer and offer data, including deduplication logic.

    Functional Requirements Addressed:
    - FR2: Basic column-level data validation.
    - FR10: Receives real-time data from Insta or E-aggregators.
    - FR11: Modifies existing APIs to insert E-aggregator data directly into CDP.
    - FR18: Handles 'Enrich' offers logic.
    - NFR8: Performs basic column-level data validation during data ingestion.
    - NFR9: Lead Generation API validates data before pushing records to CDP.

    Request Body Example (from system_design.api_endpoints):
    {
      "source_system": "E-aggregator-X",
      "data_type": "Lead",
      "payload": {
        "mobile_number": "9876543210",
        "pan_number": "ABCDE1234F",
        "offer_details": {
          "offer_type": "Fresh",
          "amount": 50000,
          "valid_until": "2023-12-31T23:59:59Z"
        }
      }
    }

    Response Example (from system_design.api_endpoints):
    {
      "status": "success",
      "message": "Data processed successfully",
      "customer_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Request must contain JSON data"}), 400

    # Validate the incoming payload structure and content
    is_valid, errors = validate_e_aggregator_payload(data)

    if not is_valid:
        return jsonify({"status": "error", "message": "Validation failed", "errors": errors}), 400

    try:
        source_system = data.get('source_system')
        data_type = data.get('data_type')
        payload = data.get('payload')

        # Delegate to a service function that encapsulates the core business logic:
        # - Customer creation/update based on deduplication keys (FR1, FR3, FR4, FR5)
        # - Offer creation/update, including handling 'Enrich' offers (FR16, FR17, FR18)
        # - Interaction with Customer 360 for 'live book' deduplication (FR5)
        # - Storing offer history (FR20)
        # The service is expected to return a dictionary containing at least 'customer_id'
        # and a 'message' upon successful processing.
        processing_result = process_e_aggregator_offer(source_system, data_type, payload)

        # Ensure customer_id is a string for JSON serialization
        customer_id_str = str(processing_result.get("customer_id")) if processing_result.get("customer_id") else None

        return jsonify({
            "status": "success",
            "message": processing_result.get("message", "Data processed successfully"),
            "customer_id": customer_id_str
        }), 200

    except ValueError as e:
        # Catch specific business logic errors, e.g., invalid data format within payload
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        # Catch any unexpected errors during processing and rollback the transaction
        db.session.rollback()
        return jsonify({"status": "error", "message": f"An internal server error occurred: {str(e)}"}), 500