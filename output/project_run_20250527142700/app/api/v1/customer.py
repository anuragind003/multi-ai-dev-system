from flask import Blueprint, jsonify, abort, current_app
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
import uuid # Not strictly needed for path parameter, but useful for UUID object handling

# Define the blueprint for customer routes
# The URL prefix is '/api/customer' as per system design
customer_bp = Blueprint('customer_v1', __name__, url_prefix='/api/customer')

@customer_bp.route('/<uuid:customer_id>', methods=['GET'])
def get_customer_profile(customer_id: uuid.UUID):
    """
    Retrieves a single customer's profile view with associated offers and application stages.

    FR2: The system shall provide a single profile view of the customer for Consumer Loan Products.
    FR36: The system shall provide a front-end for customer level view with stages.

    Args:
        customer_id (uuid.UUID): The UUID of the customer to retrieve.

    Returns:
        JSON response: A dictionary containing customer details, active offers, and application stages.
        HTTP Status Code: 200 on success, 404 if customer not found, 500 on internal error.
    """
    current_app.logger.info(f"Attempting to retrieve customer profile for ID: {customer_id}")
    try:
        # Query the Customer with joined offers and customer events
        # Use joinedload to efficiently fetch related data in one query
        customer = db.session.query(Customer).options(
            joinedload(Customer.offers).load_only(
                Offer.offer_id, Offer.offer_type, Offer.offer_status,
                Offer.propensity_flag, Offer.offer_start_date, Offer.offer_end_date,
                Offer.loan_application_number, Offer.attribution_channel
            ),
            joinedload(Customer.customer_events).load_only(
                CustomerEvent.event_id, CustomerEvent.event_type,
                CustomerEvent.event_source, CustomerEvent.event_timestamp,
                CustomerEvent.event_details
            )
        ).filter(Customer.customer_id == customer_id).first()

        if not customer:
            current_app.logger.warning(f"Customer with ID {customer_id} not found.")
            abort(404, description=f"Customer with ID {customer_id} not found.")

        # Prepare active offers list
        active_offers = []
        for offer in customer.offers:
            if offer.offer_status == 'Active': # FR15: Maintain flags for Offer statuses: Active, Inactive, and Expired
                active_offers.append({
                    "offer_id": str(offer.offer_id),
                    "offer_type": offer.offer_type,
                    "offer_status": offer.offer_status,
                    "propensity_flag": offer.propensity_flag,
                    "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
                    "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                    "loan_application_number": offer.loan_application_number,
                    "attribution_channel": offer.attribution_channel
                })

        # Prepare application stages list (FR22: Event data shall include application stages from LOS)
        application_stage_event_types = [
            'APP_STAGE_LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS', 'EKYC',
            'BANK_DETAILS', 'OTHER_DETAILS', 'E_SIGN'
        ]
        application_stages = []
        for event in customer.customer_events:
            if event.event_type in application_stage_event_types:
                application_stages.append({
                    "event_id": str(event.event_id),
                    "event_type": event.event_type,
                    "event_source": event.event_source,
                    "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                    "event_details": event.event_details
                })
        
        # Sort application stages by timestamp to show chronological journey
        application_stages.sort(key=lambda x: x['event_timestamp'] if x['event_timestamp'] else '')

        # Construct the response data
        response_data = {
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan": customer.pan,
            "customer_segment": customer.customer_segment, # FR14, FR19: Maintain different customer attributes and segments
            "active_offers": active_offers,
            "application_stages": application_stages
        }

        current_app.logger.info(f"Successfully retrieved customer profile for ID: {customer_id}")
        return jsonify(response_data), 200

    except SQLAlchemyError as e:
        # Rollback in case of database errors
        db.session.rollback()
        current_app.logger.error(f"Database error while fetching customer {customer_id}: {e}")
        abort(500, description="An internal server error occurred while accessing the database.")
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred while fetching customer {customer_id}: {e}")
        abort(500, description="An unexpected internal server error occurred.")