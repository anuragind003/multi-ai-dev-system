from flask import Blueprint, request, jsonify
from backend.src.models import db, Event, Customer, Offer # Assuming models are defined in backend/src/models.py
import uuid
from datetime import datetime
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the blueprint for event-related routes
# The name 'event_routes_bp' is chosen to match the file name convention
# and avoid potential conflicts if 'events_bp' is used elsewhere.
event_routes_bp = Blueprint('event_routes', __name__, url_prefix='/events')

@event_routes_bp.route('/moengage', methods=['POST'])
def receive_moengage_event():
    """
    API endpoint to receive SMS campaign events (sent, delivered, click) from Moengage.
    FR25: The CDP system shall capture and store SMS events (sent, delivered, click) from Moengage.
    Expected Request Body:
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
            logging.warning("Moengage event: No JSON data received.")
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        customer_mobile = data.get('customer_mobile')
        event_type = data.get('event_type')
        timestamp_str = data.get('timestamp')
        campaign_id = data.get('campaign_id')
        details = data.get('details', {})

        if not all([customer_mobile, event_type, timestamp_str, campaign_id]):
            logging.warning(f"Moengage event: Missing required fields. Received: {data}")
            return jsonify({"status": "error", "message": "Missing required fields: customer_mobile, event_type, timestamp, campaign_id"}), 400

        try:
            # Handle 'Z' for UTC timezone in ISO 8601 strings
            event_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            logging.warning(f"Moengage event: Invalid timestamp format received: {timestamp_str}")
            return jsonify({"status": "error", "message": "Invalid timestamp format. Use ISO 8601."}), 400

        customer_id = None
        offer_id = None

        # Find customer by mobile number
        customer = Customer.query.filter_by(mobile_number=customer_mobile).first()
        if customer:
            customer_id = customer.customer_id
        else:
            # As per BRD, customer data should be pre-ingested. If not found, it's an issue.
            logging.error(f"Moengage event received for unknown customer mobile: {customer_mobile}. Event not recorded.")
            return jsonify({"status": "error", "message": f"Customer with mobile number {customer_mobile} not found. Event cannot be linked."}), 404

        # Attempt to find an offer if offer_id is explicitly provided in details.
        # The API spec does not mandate offer_id in the top-level payload for Moengage events.
        if 'offer_id' in details:
            try:
                # Validate if it's a valid UUID
                offer_uuid_from_details = uuid.UUID(details['offer_id'])
                # Check if the offer exists and belongs to the identified customer
                offer = Offer.query.filter_by(offer_id=offer_uuid_from_details, customer_id=customer_id).first()
                if offer:
                    offer_id = offer.offer_id
                else:
                    logging.warning(f"Moengage event: Offer ID {details['offer_id']} in details not found or does not belong to customer {customer_id}. Event will be recorded without offer_id linkage.")
            except ValueError:
                logging.warning(f"Moengage event: Invalid UUID format for offer_id in details: {details['offer_id']}. Event will be recorded without offer_id linkage.")

        new_event = Event(
            event_id=uuid.uuid4(),
            customer_id=customer_id,
            offer_id=offer_id, # This can be None if no matching offer is found or provided
            event_type=event_type,
            event_timestamp=event_timestamp,
            source_system='Moengage',
            event_details=details
        )

        db.session.add(new_event)
        db.session.commit()
        logging.info(f"Moengage event recorded: Type='{event_type}', Customer='{customer_id}', Campaign='{campaign_id}', Event ID='{new_event.event_id}'")
        return jsonify({"status": "success", "message": "Moengage event recorded", "event_id": str(new_event.event_id)}), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error processing Moengage event: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error", "details": str(e)}), 500

@event_routes_bp.route('/los', methods=['POST'])
def receive_los_event():
    """
    API endpoint to receive loan application journey and conversion events (EKYC, Disbursement) from LOS.
    FR26: The CDP system shall capture and store conversion events (EKYC achieved, Disbursement) from LOS/Moengage.
    FR27: The CDP system shall capture and store loan application journey stages (login, bureau check, offer details, eKYC, Bank details, other details, e-sign) from LOS.
    Expected Request Body:
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
            logging.warning("LOS event: No JSON data received.")
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        loan_application_number = data.get('loan_application_number')
        event_type = data.get('event_type')
        timestamp_str = data.get('timestamp')
        customer_id_str = data.get('customer_id') # This is expected to be a UUID string
        details = data.get('details', {})

        if not all([loan_application_number, event_type, timestamp_str, customer_id_str]):
            logging.warning(f"LOS event: Missing required fields. Received: {data}")
            return jsonify({"status": "error", "message": "Missing required fields: loan_application_number, event_type, timestamp, customer_id"}), 400

        try:
            event_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            logging.warning(f"LOS event: Invalid timestamp format received: {timestamp_str}")
            return jsonify({"status": "error", "message": "Invalid timestamp format. Use ISO 8601."}), 400

        try:
            customer_uuid = uuid.UUID(customer_id_str)
        except ValueError:
            logging.warning(f"LOS event: Invalid customer_id format received: {customer_id_str}")
            return jsonify({"status": "error", "message": "Invalid customer_id format. Must be a valid UUID."}), 400

        customer = Customer.query.get(customer_uuid)
        if not customer:
            logging.error(f"LOS event received for unknown customer ID: {customer_id_str}. Event not recorded.")
            return jsonify({"status": "error", "message": f"Customer with ID {customer_id_str} not found. Event cannot be linked."}), 404

        offer_id = None
        # Find offer by loan_application_number
        # Assuming loan_application_number is unique for an active offer, or we pick the first match.
        offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()
        if offer:
            offer_id = offer.offer_id
            # Optional: Verify if the offer belongs to the customer_id provided.
            # If not, it's a data inconsistency, but we can still record the event.
            if offer.customer_id != customer.customer_id:
                logging.warning(f"LOS event: Offer (LAN: {loan_application_number}, Offer ID: {offer_id}) found but linked to customer {offer.customer_id}, not {customer.customer_id} from payload. Event will be linked to payload customer and found offer.")
        else:
            logging.warning(f"LOS event received for unknown loan application number: {loan_application_number}. Event will be recorded without offer_id linkage.")
            # It's possible an event comes before the offer is fully processed or linked with LAN.
            # Allow offer_id to be None as per schema.

        new_event = Event(
            event_id=uuid.uuid4(),
            customer_id=customer.customer_id,
            offer_id=offer_id, # This can be None if no matching offer is found
            event_type=event_type,
            event_timestamp=event_timestamp,
            source_system='LOS',
            event_details=details
        )

        db.session.add(new_event)
        db.session.commit()
        logging.info(f"LOS event recorded: Type='{event_type}', Customer='{customer.customer_id}', LAN='{loan_application_number}', Event ID='{new_event.event_id}'")
        return jsonify({"status": "success", "message": "LOS event recorded", "event_id": str(new_event.event_id)}), 201

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error processing LOS event: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error", "details": str(e)}), 500