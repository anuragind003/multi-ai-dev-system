from flask import Blueprint, request, jsonify, abort
import uuid
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from backend.database.db_config import db_session
from backend.models import Customer, Offer, Event

api_ingestion_bp = Blueprint('api_ingestion', __name__)


@api_ingestion_bp.route('/api/leads', methods=['POST'])
def receive_leads():
    """
    Receives real-time lead generation data from Insta/E-aggregators
    and inserts/updates customer data in CDP.
    """
    data = request.get_json()
    if not data:
        abort(400, description="Request must contain JSON data.")

    mobile_number = data.get('mobile_number')
    pan_number = data.get('pan_number')
    aadhaar_number = data.get('aadhaar_number')
    loan_type = data.get('loan_type')
    source_channel = data.get('source_channel')

    if not (mobile_number or pan_number or aadhaar_number):
        abort(400, description="At least one of mobile_number, pan_number, "
                              "or aadhaar_number is required.")

    try:
        with db_session() as session:
            customer = None
            if mobile_number:
                customer = session.query(Customer).filter_by(
                    mobile_number=mobile_number).first()
            if not customer and pan_number:
                customer = session.query(Customer).filter_by(
                    pan_number=pan_number).first()
            if not customer and aadhaar_number:
                customer = session.query(Customer).filter_by(
                    aadhaar_number=aadhaar_number).first()

            if customer:
                # Customer exists, update relevant fields if necessary
                # For simplicity, we just return existing customer_id.
                # More complex logic for updating existing customer attributes
                # or creating new offers/events would go here.
                pass
            else:
                # Create a new customer
                customer_id = str(uuid.uuid4())
                new_customer = Customer(
                    customer_id=customer_id,
                    mobile_number=mobile_number,
                    pan_number=pan_number,
                    aadhaar_number=aadhaar_number
                    # Other fields like segment, dnd_flag can be set with defaults
                    # or based on further logic.
                )
                session.add(new_customer)
                customer = new_customer

            # Log an event for lead generation
            event_id = str(uuid.uuid4())
            new_event = Event(
                event_id=event_id,
                customer_id=customer.customer_id,
                event_type="LEAD_GENERATED",
                event_source=source_channel,
                event_timestamp=datetime.now(),
                event_details={
                    "loan_type": loan_type,
                    "mobile_number": mobile_number,
                    "pan_number": pan_number,
                    "aadhaar_number": aadhaar_number
                }
            )
            session.add(new_event)
            session.commit()

            return jsonify({
                "status": "success",
                "customer_id": customer.customer_id
            }), 200

    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error during lead ingestion: {e}")
        abort(500, description="Failed to process lead due to a database error.")
    except Exception as e:
        print(f"An unexpected error occurred during lead ingestion: {e}")
        abort(500, description="An unexpected error occurred.")


@api_ingestion_bp.route('/api/eligibility', methods=['POST'])
def update_eligibility():
    """
    Receives real-time eligibility data from Insta/E-aggregators
    and updates customer/offer data.
    """
    data = request.get_json()
    if not data:
        abort(400, description="Request must contain JSON data.")

    customer_id = data.get('customer_id')
    offer_id = data.get('offer_id')
    eligibility_status = data.get('eligibility_status')
    loan_amount = data.get('loan_amount')
    source_channel = data.get('source_channel', 'E-aggregator') # Default source

    if not all([customer_id, offer_id, eligibility_status]):
        abort(400, description="customer_id, offer_id, and eligibility_status "
                              "are required.")

    try:
        with db_session() as session:
            customer = session.query(Customer).filter_by(
                customer_id=customer_id).first()
            if not customer:
                abort(404, description=f"Customer with ID {customer_id} not found.")

            offer = session.query(Offer).filter_by(
                offer_id=offer_id, customer_id=customer_id).first()
            if not offer:
                abort(404, description=f"Offer with ID {offer_id} for customer "
                                      f"{customer_id} not found.")

            # Update offer status
            offer.offer_status = eligibility_status
            offer.updated_at = datetime.now()

            # Log an event for eligibility update
            event_id = str(uuid.uuid4())
            new_event = Event(
                event_id=event_id,
                customer_id=customer_id,
                event_type="ELIGIBILITY_UPDATED",
                event_source=source_channel,
                event_timestamp=datetime.now(),
                event_details={
                    "offer_id": offer_id,
                    "eligibility_status": eligibility_status,
                    "loan_amount": loan_amount
                }
            )
            session.add(new_event)
            session.commit()

            return jsonify({
                "status": "success",
                "message": "Eligibility updated successfully."
            }), 200

    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error during eligibility update: {e}")
        abort(500, description="Failed to update eligibility due to a database error.")
    except Exception as e:
        print(f"An unexpected error occurred during eligibility update: {e}")
        abort(500, description="An unexpected error occurred.")


@api_ingestion_bp.route('/api/status-updates', methods=['POST'])
def receive_status_updates():
    """
    Receives real-time application status updates from Insta/E-aggregators or LOS.
    """
    data = request.get_json()
    if not data:
        abort(400, description="Request must contain JSON data.")

    loan_application_number = data.get('loan_application_number')
    customer_id = data.get('customer_id')
    current_stage = data.get('current_stage')
    status_timestamp_str = data.get('status_timestamp')
    event_source = data.get('event_source', 'LOS') # Default source

    if not all([loan_application_number, customer_id, current_stage,
                status_timestamp_str]):
        abort(400, description="loan_application_number, customer_id, "
                              "current_stage, and status_timestamp are required.")

    try:
        status_timestamp = datetime.fromisoformat(status_timestamp_str)
    except ValueError:
        abort(400, description="Invalid status_timestamp format. "
                              "Expected ISO format (e.g., YYYY-MM-DDTHH:MM:SS).")

    try:
        with db_session() as session:
            customer = session.query(Customer).filter_by(
                customer_id=customer_id).first()
            if not customer:
                abort(404, description=f"Customer with ID {customer_id} not found.")

            # Log the application stage as an event
            event_id = str(uuid.uuid4())
            new_event = Event(
                event_id=event_id,
                customer_id=customer_id,
                event_type=current_stage, # e.g., 'LOAN_LOGIN', 'EKYC_ACHIEVED'
                event_source=event_source,
                event_timestamp=status_timestamp,
                event_details={
                    "loan_application_number": loan_application_number,
                    "stage_details": data # Store full payload for flexibility
                }
            )
            session.add(new_event)
            session.commit()

            return jsonify({
                "status": "success",
                "message": "Status updated successfully."
            }), 200

    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error during status update: {e}")
        abort(500, description="Failed to update status due to a database error.")
    except Exception as e:
        print(f"An unexpected error occurred during status update: {e}")
        abort(500, description="An unexpected error occurred.")