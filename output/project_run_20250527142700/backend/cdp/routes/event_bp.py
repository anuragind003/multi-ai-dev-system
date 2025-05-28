from flask import Blueprint, request, jsonify
from backend.models import db, Event, Customer, Offer # Assuming models are defined in backend/models.py
import uuid
from datetime import datetime
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the blueprint for event-related routes
# The name 'events_bp' is consistent with how it's imported in backend/__init__.py
events_bp = Blueprint('events_bp', __name__, url_prefix='/events')

@events_bp.route('/moengage', methods=['POST'])
def receive_moengage_event():
    """
    API endpoint to receive SMS campaign events (sent, delivered, click) from Moengage.

    Functional Requirements Addressed:
    - FR23: The CDP system shall store event data from Moengage and LOS.
    - FR25: The CDP system shall capture and store SMS events (sent, delivered, click) from Moengage.
    - FR26: The CDP system shall capture and store conversion events (EKYC achieved, Disbursement) from LOS/Moengage.

    Request Body Example (from system_design.api_endpoints):
    {
      "customer_mobile": "string",
      "event_type": "string",
      "timestamp": "string",
      "campaign_id": "string",
      "details": {}
    }
    """
    try:
        data = request.get_json()
        if not data:
            logging.error("Moengage event: No JSON payload received.")
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        customer_mobile = data.get('customer_mobile')
        event_type = data.get('event_type')
        timestamp_str = data.get('timestamp')
        campaign_id = data.get('campaign_id')
        details = data.get('details', {})

        if not all([customer_mobile, event_type, timestamp_str]):
            logging.error(f"Moengage event: Missing required fields. Payload: {data}")
            return jsonify({"status": "error", "message": "Missing required fields: customer_mobile, event_type, timestamp"}), 400

        try:
            # Handle ISO 8601 format, including 'Z' for UTC offset
            event_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            logging.error(f"Moengage event: Invalid timestamp format '{timestamp_str}'. Expected ISO 8601.")
            return jsonify({"status": "error", "message": "Invalid timestamp format. Expected ISO 8601."}), 400

        # Attempt to find the customer by mobile number
        customer = Customer.query.filter_by(mobile_number=customer_mobile).first()
        customer_id = customer.customer_id if customer else None

        if not customer_id:
            logging.warning(f"Moengage event received for mobile number '{customer_mobile}' not found in CDP. Event will be recorded without customer_id link.")
            # Depending on business rules, a new customer could be created here,
            # or an error returned if linking is strictly mandatory.
            # For now, we proceed as customer_id in 'events' table is nullable.

        # For Moengage events, offer_id is typically not directly provided in the API spec.
        # If there's a way to infer it from campaign_id or other details,
        # that logic would be implemented here. For now, it remains None.
        offer_id = None

        new_event = Event(
            event_id=uuid.uuid4(),
            customer_id=customer_id,
            offer_id=offer_id,
            event_type=event_type,
            event_timestamp=event_timestamp,
            source_system='Moengage',
            event_details={
                "campaign_id": campaign_id,
                "customer_mobile_at_event": customer_mobile, # Store mobile in details for traceability
                **details
            }
        )

        db.session.add(new_event)
        db.session.commit()

        logging.info(f"Moengage event '{event_type}' recorded successfully for mobile: {customer_mobile}.")
        return jsonify({"status": "success", "message": "Moengage event recorded", "event_id": str(new_event.event_id)}), 201

    except Exception as e:
        db.session.rollback() # Rollback in case of any database error
        logging.exception(f"Error processing Moengage event: {e}") # Use exception for full traceback
        return jsonify({"status": "error", "message": "Internal server error", "details": str(e)}), 500

@events_bp.route('/los', methods=['POST'])
def receive_los_event():
    """
    API endpoint to receive loan application journey and conversion events (EKYC, Disbursement) from LOS.

    Functional Requirements Addressed:
    - FR23: The CDP system shall store event data from Moengage and LOS.
    - FR26: The CDP system shall capture and store conversion events (EKYC achieved, Disbursement) from LOS/Moengage.
    - FR27: The CDP system shall capture and store loan application journey stages (login, bureau check, offer details, eKYC, Bank details, other details, e-sign) from LOS.

    Request Body Example (from system_design.api_endpoints):
    {
      "loan_application_number": "string",
      "event_type": "string",
      "timestamp": "string",
      "customer_id": "string",
      "details": {}
    }
    """
    try:
        data = request.get_json()
        if not data:
            logging.error("LOS event: No JSON payload received.")
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        loan_application_number = data.get('loan_application_number')
        event_type = data.get('event_type')
        timestamp_str = data.get('timestamp')
        customer_id_from_payload = data.get('customer_id') # Optional, for direct linking
        details = data.get('details', {})

        if not all([loan_application_number, event_type, timestamp_str]):
            logging.error(f"LOS event: Missing required fields. Payload: {data}")
            return jsonify({"status": "error", "message": "Missing required fields: loan_application_number, event_type, timestamp"}), 400

        try:
            event_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            logging.error(f"LOS event: Invalid timestamp format '{timestamp_str}'. Expected ISO 8601.")
            return jsonify({"status": "error", "message": "Invalid timestamp format. Expected ISO 8601."}), 400

        # Attempt to find the offer and associated customer based on loan_application_number
        offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()
        offer_id = offer.offer_id if offer else None
        customer_id = offer.customer_id if offer else None

        # If customer_id is provided in the payload and an offer was not found,
        # or if the customer_id from payload is different, prioritize/validate.
        # For simplicity, if offer is found, its customer_id is preferred.
        # If offer not found, try to use customer_id from payload.
        if not customer_id and customer_id_from_payload:
            try:
                # Validate if it's a valid UUID string
                uuid.UUID(customer_id_from_payload)
                # Check if this customer_id actually exists in the Customer table
                existing_customer = Customer.query.get(customer_id_from_payload)
                if existing_customer:
                    customer_id = customer_id_from_payload
                else:
                    logging.warning(f"LOS event received with customer_id '{customer_id_from_payload}' not found in CDP. Event will be recorded without customer_id link.")
            except ValueError:
                logging.warning(f"LOS event received with invalid customer_id format in payload: '{customer_id_from_payload}'.")
                # customer_id remains None if invalid format

        if not offer_id:
            logging.warning(f"LOS event received for loan application number '{loan_application_number}' not found in CDP. Event will be recorded without offer_id link.")
            if not customer_id:
                logging.warning(f"LOS event for LAN '{loan_application_number}' also has no valid customer_id. Event recorded without customer or offer link.")

        new_event = Event(
            event_id=uuid.uuid4(),
            customer_id=customer_id,
            offer_id=offer_id,
            event_type=event_type,
            event_timestamp=event_timestamp,
            source_system='LOS',
            event_details={
                "loan_application_number_at_event": loan_application_number, # Store LAN in details for traceability
                **details
            }
        )

        db.session.add(new_event)
        db.session.commit()

        logging.info(f"LOS event '{event_type}' recorded successfully for LAN: {loan_application_number}.")
        return jsonify({"status": "success", "message": "LOS event recorded", "event_id": str(new_event.event_id)}), 201

    except Exception as e:
        db.session.rollback() # Rollback in case of any database error
        logging.exception(f"Error processing LOS event: {e}") # Use exception for full traceback
        return jsonify({"status": "error", "message": "Internal server error", "details": str(e)}), 500