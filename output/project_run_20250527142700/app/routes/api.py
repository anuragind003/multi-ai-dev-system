from flask import Blueprint, request, jsonify, current_app
from app import db  # Assuming db is initialized in app/__init__.py or app.py
from app.models import Customer, Offer, CustomerEvent
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
import uuid  # Not strictly needed for these endpoints, but often useful for IDs

# Define the blueprint for real-time API routes
# This blueprint will handle /api/eligibility and /api/status
# The name 'realtime_api' aligns with the hint in app.py's blueprint registration.
realtime_api_bp = Blueprint('realtime_api', __name__, url_prefix='/api')

@realtime_api_bp.route('/eligibility', methods=['POST'])
def process_eligibility():
    """
    Receives real-time eligibility check data from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Eligibility API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    mobile_number = data.get('mobile_number')
    loan_application_number = data.get('loan_application_number')  # Optional, but useful for context
    eligibility_status = data.get('eligibility_status')
    offer_id = data.get('offer_id')

    if not all([mobile_number, eligibility_status]):
        return jsonify({"status": "error", "message": "Missing required fields: mobile_number, eligibility_status"}), 400

    try:
        # Find customer by mobile number. For eligibility, a customer should typically exist.
        customer = Customer.query.filter_by(mobile_number=mobile_number).first()
        if not customer:
            # If customer not found, it's a 404 or a data issue.
            # Eligibility implies a customer profile should already be in CDP.
            return jsonify({"status": "error", "message": f"Customer with mobile number {mobile_number} not found."}), 404

        offer = None
        if offer_id:
            offer = Offer.query.filter_by(offer_id=offer_id).first()
            if not offer:
                current_app.logger.warning(f"Offer with ID {offer_id} not found for eligibility update. Proceeding without offer link.")
        elif loan_application_number:
            # If offer_id is not provided, try to find offer by loan_application_number
            offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()
            if not offer:
                current_app.logger.warning(f"Offer with LAN {loan_application_number} not found for eligibility update. Proceeding without offer link.")

        # Create a CustomerEvent record
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type=f"ELIGIBILITY_CHECK_{eligibility_status.upper()}",
            event_source="E-AGGREGATOR",  # Or 'Insta' based on actual source
            event_details={
                "loan_application_number": loan_application_number,
                "eligibility_status": eligibility_status,
                "offer_id": str(offer.offer_id) if offer else None
            }
        )
        db.session.add(event)

        # Update offer status based on eligibility. This logic can be refined based on business rules.
        if offer:
            if eligibility_status.lower() == 'eligible':
                # If an offer was previously inactive/pending, it might become active
                if offer.offer_status in ['Inactive', 'Pending']:
                    offer.offer_status = 'Active'
                offer.updated_at = datetime.utcnow()
            elif eligibility_status.lower() == 'not_eligible':
                # Mark offer as inactive or expired if not eligible
                offer.offer_status = 'Inactive'
                offer.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"status": "success", "message": "Eligibility data processed"}), 200

    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error processing eligibility: {e}")
        return jsonify({"status": "error", "message": "Data integrity issue, possibly duplicate entry or invalid reference."}), 409
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error processing eligibility: {e}")
        return jsonify({"status": "error", "message": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error processing eligibility: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@realtime_api_bp.route('/status', methods=['POST'])
def process_status_update():
    """
    Receives real-time loan application status updates from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Status API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    FR22: Event data shall include application stages (login, bureau check, offer details, eKYC, Bank details, other details, e-sign) (from LOS).
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    loan_application_number = data.get('loan_application_number')
    application_stage = data.get('application_stage')
    status_details = data.get('status_details')
    event_timestamp_str = data.get('event_timestamp')  # ISO format string

    if not all([loan_application_number, application_stage]):
        return jsonify({"status": "error", "message": "Missing required fields: loan_application_number, application_stage"}), 400

    try:
        event_timestamp = datetime.fromisoformat(event_timestamp_str) if event_timestamp_str else datetime.utcnow()
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid event_timestamp format. Use ISO 8601."}), 400

    try:
        # Find the associated offer using loan_application_number
        offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()

        customer_id = None
        if offer:
            customer_id = offer.customer_id
        else:
            # If no offer found, try to find customer by other means if available in the payload,
            # e.g., mobile_number, PAN, etc. For now, assume loan_application_number is primary.
            # If no offer and no direct customer identifier, we cannot link the event.
            current_app.logger.warning(f"Offer not found for loan_application_number: {loan_application_number}. Cannot link event directly to an offer.")
            # In a real system, you might attempt to find the customer via other identifiers
            # passed in the payload, or log this as an unlinked event.
            # For this MVP, if no offer and thus no customer_id, we return 404.

        if not customer_id:
            return jsonify({"status": "error", "message": f"Customer or Offer not found for loan application {loan_application_number}. Cannot log event."}), 404

        # Create a CustomerEvent record for the application stage
        event = CustomerEvent(
            customer_id=customer_id,
            event_type=f"APP_STAGE_{application_stage.upper()}",
            event_source="LOS",  # As per FR22
            event_timestamp=event_timestamp,
            event_details={
                "loan_application_number": loan_application_number,
                "application_stage": application_stage,
                "status_details": status_details,
                "offer_id": str(offer.offer_id) if offer else None  # Link to offer if found
            }
        )
        db.session.add(event)

        # Update offer status based on the application stage
        # FR13: prevent modification of customer offers with started loan application journeys until expired/rejected.
        # FR37: expiry logic for non-journey started customers.
        # FR38: mark offers as expired if LAN validity post journey start is over.
        if offer:
            # Example logic for offer status updates based on application stage
            if application_stage.lower() in ['rejected', 'cancelled', 'expired']:
                offer.offer_status = 'Expired'  # Or 'Rejected'
                offer.updated_at = datetime.utcnow()
            elif application_stage.lower() == 'disbursed':  # Assuming 'disbursed' means conversion
                offer.offer_status = 'Converted'
                offer.updated_at = datetime.utcnow()
            # For intermediate stages like 'login', 'bureau_check', etc., the offer status
            # typically remains 'Active' or 'In-Journey' and is not modified by these events
            # unless specific business logic dictates. FR13 implies offers with started journeys
            # should not be modified until expired/rejected.

        db.session.commit()
        return jsonify({"status": "success", "message": "Status updated"}), 200

    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error processing status update: {e}")
        return jsonify({"status": "error", "message": "Data integrity issue, possibly duplicate entry or invalid reference."}), 409
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error processing status update: {e}")
        return jsonify({"status": "error", "message": "Database error occurred."}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error processing status update: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500