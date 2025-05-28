from flask import Blueprint, jsonify, abort, current_app
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
import uuid # Used for type hinting the customer_id parameter

# Define the blueprint for customer routes
# The URL prefix is '/api/customer' as per system design
customer_bp = Blueprint('customer', __name__, url_prefix='/api/customer')

@customer_bp.route('/<uuid:customer_id>', methods=['GET'])
def get_customer_profile(customer_id: uuid.UUID):
    """
    Retrieves a single customer's profile view with associated offers and application stages.

    FR2: The system shall provide a single profile view of the customer for Consumer Loan Products.
    FR36: The system shall provide a front-end for customer level view with stages.
    """
    current_app.logger.info(f"Attempting to retrieve customer profile for ID: {customer_id}")
    try:
        # Query the customer, eagerly loading related offers and customer events
        customer = db.session.query(Customer).options(
            joinedload(Customer.offers),
            joinedload(Customer.customer_events)
        ).filter_by(customer_id=customer_id).first()

        if not customer:
            current_app.logger.warning(f"Customer with ID {customer_id} not found.")
            abort(404, description="Customer not found")

        # Prepare active offers based on 'Active' status
        active_offers = []
        for offer in customer.offers:
            if offer.offer_status == 'Active':
                active_offers.append({
                    "offer_id": str(offer.offer_id),
                    "offer_type": offer.offer_type,
                    "offer_status": offer.offer_status,
                    "propensity_flag": offer.propensity_flag,
                    "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
                    "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                    "loan_application_number": offer.loan_application_number,
                    "attribution_channel": offer.attribution_channel,
                    "created_at": offer.created_at.isoformat() if offer.created_at else None,
                    "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
                })

        # Prepare application stages from customer events
        # Assuming application stage events are identified by 'APP_STAGE_' prefix in event_type
        application_stages = []
        for event in customer.customer_events:
            if event.event_type and event.event_type.startswith('APP_STAGE_'):
                application_stages.append({
                    "event_id": str(event.event_id),
                    "event_type": event.event_type,
                    "event_source": event.event_source,
                    "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                    "event_details": event.event_details # JSONB field, should be directly serializable
                })
        # Sort application stages by timestamp for chronological view
        application_stages.sort(key=lambda x: x['event_timestamp'] if x['event_timestamp'] else '')

        # Construct the customer profile data
        customer_data = {
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan": customer.pan,
            "aadhaar_ref_number": customer.aadhaar_ref_number,
            "ucid": customer.ucid,
            "previous_loan_app_number": customer.previous_loan_app_number,
            "customer_attributes": customer.customer_attributes, # JSONB field
            "customer_segment": customer.customer_segment,
            "is_dnd": customer.is_dnd,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
            "active_offers": active_offers,
            "application_stages": application_stages
        }

        current_app.logger.info(f"Successfully retrieved customer profile for ID: {customer_id}")
        return jsonify(customer_data)

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error retrieving customer {customer_id}: {e}")
        db.session.rollback() # Rollback in case of database error to clean the session
        abort(500, description="Database error occurred while retrieving customer profile.")
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred retrieving customer {customer_id}: {e}")
        abort(500, description="An unexpected error occurred.")