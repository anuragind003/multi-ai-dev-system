from flask import Blueprint, request, jsonify
from backend.database import db
from backend.models import Customer, Offer, OfferHistory, Event # Assuming these models are defined in backend.models
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

    Functional Requirements: FR10, FR11
    Non-Functional Requirements: NFR2, NFR8, NFR9
    """
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    # Perform basic column-level data validation (FR2, NFR8, NFR9)
    validation_errors = validate_e_aggregator_payload(data)
    if validation_errors:
        # Return 400 Bad Request if validation fails
        return jsonify({"status": "error", "message": "Validation failed", "errors": validation_errors}), 400

    source_system = data.get('source_system')
    data_type = data.get('data_type')
    payload = data.get('payload')

    # Ensure the core payload structure is present for processing
    if not all(k in payload for k in ['mobile_number', 'pan_number', 'offer_details']):
        return jsonify({
            "status": "error",
            "message": "Payload missing essential customer/offer details (e.g., mobile_number, pan_number, offer_details)"
        }), 400

    try:
        # Delegate the complex business logic (customer creation/update,
        # offer processing, deduplication, offer attribution, etc.) to a service layer.
        # This keeps the route handler clean and focused on request/response.
        customer_id, offer_id, processing_message = process_e_aggregator_offer(
            source_system=source_system,
            data_type=data_type,
            payload=payload
        )

        # Commit the transaction if all operations in the service layer were successful
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": processing_message,
            "customer_id": str(customer_id),
            "offer_id": str(offer_id) if offer_id else None
        }), 200

    except ValueError as e:
        # Catch specific business logic errors (e.g., invalid data, conflict)
        db.session.rollback() # Rollback any changes made in the session
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        # Catch any unexpected internal server errors
        db.session.rollback() # Rollback any changes made in the session
        print(f"Error during E-aggregator data ingestion: {e}") # Log the error for debugging
        return jsonify({"status": "error", "message": "An internal server error occurred during ingestion."}), 500

# Placeholder for other ingestion routes, if they were to be implemented
# For example, a route for daily batch ingestion from Offermart (FR8, NFR3)
# This would likely involve a different mechanism, e.g., file upload or triggering a background job.
# @ingestion_bp.route('/offermart-daily-feed', methods=['POST'])
# def ingest_offermart_daily_feed():
#     """
#     Endpoint for daily ingestion of Offer and Customer data from Offermart.
#     This would typically involve processing a larger dataset, possibly from a file upload
#     or a direct database connection/API call from Offermart's side.
#     """
#     # Logic for processing Offermart data
#     # This would also involve validation, deduplication, and offer management.
#     return jsonify({"status": "info", "message": "Offermart daily feed ingestion endpoint (implementation pending)"}), 202 # 202 Accepted for async processing