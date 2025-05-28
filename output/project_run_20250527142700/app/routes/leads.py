from flask import Blueprint, request, jsonify, current_app
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, timedelta

# Define the blueprint for lead-related routes
# The url_prefix='/api' ensures that routes defined here are accessible under /api/leads, /api/eligibility, etc.
leads_bp = Blueprint('leads', __name__, url_prefix='/api')

@leads_bp.route('/leads', methods=['POST'])
def create_lead():
    """
    Receives real-time lead generation data from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    FR1: The system shall perform basic column-level validation.
    FR2, FR3, FR4, FR5: The system shall perform deduplication. (Simplified for real-time API)
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("Lead creation failed: No JSON data provided.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    # Basic validation for required fields
    mobile_number = data.get('mobile_number')
    loan_type = data.get('loan_type')
    source_channel = data.get('source_channel')
    application_id = data.get('application_id') # This might be an initial application ID or a lead ID

    if not mobile_number or not loan_type or not source_channel:
        current_app.logger.warning(f"Lead creation failed: Missing required fields. Data: {data}")
        return jsonify({"status": "error", "message": "Missing required fields: mobile_number, loan_type, source_channel"}), 400

    pan = data.get('pan')
    aadhaar_ref_number = data.get('aadhaar_ref_number')
    ucid = data.get('ucid')
    previous_loan_app_number = data.get('previous_loan_app_number')

    customer = None
    try:
        # Deduplication logic (simplified for real-time API based on unique identifiers)
        # Prioritize existing customer lookup by unique identifiers
        if mobile_number:
            customer = Customer.query.filter_by(mobile_number=mobile_number).first()
        if not customer and pan:
            customer = Customer.query.filter_by(pan=pan).first()
        if not customer and aadhaar_ref_number:
            customer = Customer.query.filter_by(aadhaar_ref_number=aadhaar_ref_number).first()
        if not customer and ucid:
            customer = Customer.query.filter_by(ucid=ucid).first()
        if not customer and previous_loan_app_number:
            customer = Customer.query.filter_by(previous_loan_app_number=previous_loan_app_number).first()

        if customer:
            # Update existing customer with any new provided identifiers
            updated = False
            if not customer.pan and pan:
                customer.pan = pan
                updated = True
            if not customer.aadhaar_ref_number and aadhaar_ref_number:
                customer.aadhaar_ref_number = aadhaar_ref_number
                updated = True
            if not customer.ucid and ucid:
                customer.ucid = ucid
                updated = True
            if not customer.previous_loan_app_number and previous_loan_app_number:
                customer.previous_loan_app_number = previous_loan_app_number
                updated = True
            if updated:
                customer.updated_at = datetime.now()
                db.session.add(customer) # Ensure it's in the session for update
                db.session.commit()
                current_app.logger.info(f"Existing customer {customer.customer_id} updated with new identifiers.")
            message = "Lead processed successfully (existing customer updated)."
        else:
            # Create new customer
            customer = Customer(
                mobile_number=mobile_number,
                pan=pan,
                aadhaar_ref_number=aadhaar_ref_number,
                ucid=ucid,
                previous_loan_app_number=previous_loan_app_number,
                customer_attributes={"loan_type": loan_type, "source_channel": source_channel} # Store initial lead attributes
            )
            db.session.add(customer)
            db.session.commit()
            current_app.logger.info(f"New customer {customer.customer_id} created from lead.")
            message = "Lead processed successfully (new customer created)."

        # Create an initial offer or event for the lead if an application_id is provided
        if application_id:
            # Check if an offer with this application_id already exists for this customer
            existing_offer = Offer.query.filter_by(customer_id=customer.customer_id, loan_application_number=application_id).first()
            if not existing_offer:
                new_offer = Offer(
                    customer_id=customer.customer_id,
                    offer_type='Fresh', # Or 'Lead-generated' based on business logic
                    offer_status='Active',
                    loan_application_number=application_id,
                    attribution_channel=source_channel,
                    offer_start_date=datetime.now().date(),
                    offer_end_date=datetime.now().date() + timedelta(days=30) # Example expiry
                )
                db.session.add(new_offer)
                db.session.commit()
                current_app.logger.info(f"New offer {new_offer.offer_id} created for customer {customer.customer_id} from lead.")
            else:
                current_app.logger.info(f"Offer with application ID {application_id} already exists for customer {customer.customer_id}.")

        # Log a customer event for lead generation
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type='LEAD_GENERATED',
            event_source=source_channel,
            event_details={"loan_type": loan_type, "application_id": application_id}
        )
        db.session.add(event)
        db.session.commit()
        current_app.logger.info(f"Lead generation event logged for customer {customer.customer_id}.")

        return jsonify({
            "status": "success",
            "message": message,
            "customer_id": str(customer.customer_id)
        }), 200

    except IntegrityError as e:
        db.session.rollback()
        # This can happen if two concurrent requests try to create the same customer
        # or update with a duplicate unique identifier (e.g., mobile_number already exists for another customer).
        current_app.logger.error(f"Integrity error during lead creation/update: {e}")
        return jsonify({"status": "error", "message": "A record with one of the provided unique identifiers already exists or a conflict occurred."}), 409 # Conflict
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during lead creation: {e}")
        return jsonify({"status": "error", "message": "Internal server error during database operation."}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error during lead creation: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@leads_bp.route('/eligibility', methods=['POST'])
def process_eligibility():
    """
    Receives real-time eligibility check data from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Eligibility API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("Eligibility processing failed: No JSON data provided.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    mobile_number = data.get('mobile_number')
    loan_application_number = data.get('loan_application_number')
    eligibility_status = data.get('eligibility_status')
    offer_id = data.get('offer_id') # Optional: if eligibility is tied to a specific existing offer

    if not mobile_number or not loan_application_number or not eligibility_status:
        current_app.logger.warning(f"Eligibility processing failed: Missing required fields. Data: {data}")
        return jsonify({"status": "error", "message": "Missing required fields: mobile_number, loan_application_number, eligibility_status"}), 400

    try:
        customer = Customer.query.filter_by(mobile_number=mobile_number).first()
        if not customer:
            current_app.logger.warning(f"Eligibility processing failed: Customer with mobile {mobile_number} not found.")
            return jsonify({"status": "error", "message": "Customer not found."}), 404

        # Find or create offer based on loan_application_number and customer_id
        offer = None
        if offer_id:
            offer = Offer.query.filter_by(offer_id=offer_id, customer_id=customer.customer_id).first()
        if not offer and loan_application_number:
            offer = Offer.query.filter_by(loan_application_number=loan_application_number, customer_id=customer.customer_id).first()

        if offer:
            # Update offer status or details if applicable
            offer.offer_status = eligibility_status # Assuming eligibility_status can map to offer_status
            offer.updated_at = datetime.now()
            db.session.add(offer)
            current_app.logger.info(f"Offer {offer.offer_id} updated with eligibility status '{eligibility_status}'.")
        else:
            # If no existing offer found, create a new one (e.g., for a new eligibility check)
            # This might need more context from the eligibility API to determine offer_type, etc.
            new_offer = Offer(
                customer_id=customer.customer_id,
                offer_type='Eligibility_Check', # A new type for offers originating from eligibility checks
                offer_status=eligibility_status,
                loan_application_number=loan_application_number,
                offer_start_date=datetime.now().date(),
                offer_end_date=datetime.now().date() + timedelta(days=7) # Example short expiry for eligibility
            )
            db.session.add(new_offer)
            offer = new_offer # Set 'offer' to the newly created one for logging below
            current_app.logger.info(f"New offer {new_offer.offer_id} created for customer {customer.customer_id} from eligibility check.")

        # Log eligibility event
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type='ELIGIBILITY_CHECK',
            event_source='E-aggregator' if 'E-aggregator' in request.url_rule.rule else 'Insta', # Infer source, adjust as needed
            event_details={
                "loan_application_number": loan_application_number,
                "eligibility_status": eligibility_status,
                "offer_id": str(offer.offer_id) if offer else None # Link to offer if available
            }
        )
        db.session.add(event)
        db.session.commit()
        current_app.logger.info(f"Eligibility event logged for customer {customer.customer_id}.")

        return jsonify({"status": "success", "message": "Eligibility data processed"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during eligibility processing: {e}")
        return jsonify({"status": "error", "message": "Internal server error during database operation."}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error during eligibility processing: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@leads_bp.route('/status', methods=['POST'])
def update_application_status():
    """
    Receives real-time loan application status updates from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Status API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    FR22: Event data shall include application stages (login, bureau check, offer details, eKYC, Bank details, other details, e-sign) (from LOS).
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("Status update failed: No JSON data provided.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    loan_application_number = data.get('loan_application_number')
    application_stage = data.get('application_stage')
    status_details = data.get('status_details')
    event_timestamp_str = data.get('event_timestamp')

    if not loan_application_number or not application_stage:
        current_app.logger.warning(f"Status update failed: Missing required fields. Data: {data}")
        return jsonify({"status": "error", "message": "Missing required fields: loan_application_number, application_stage"}), 400

    event_timestamp = None
    if event_timestamp_str:
        try:
            # Assuming ISO 8601 format (e.g., "2023-10-27T10:00:00Z" or "2023-10-27T10:00:00+05:30")
            # .replace('Z', '+00:00') handles UTC 'Z' suffix for fromisoformat
            event_timestamp = datetime.fromisoformat(event_timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            current_app.logger.warning(f"Invalid event_timestamp format: {event_timestamp_str}. Using current timestamp.")
            event_timestamp = datetime.now()
    else:
        event_timestamp = datetime.now()

    try:
        # Find the offer associated with the loan_application_number
        offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()
        if not offer:
            current_app.logger.warning(f"Status update failed: Offer with loan application number {loan_application_number} not found.")
            return jsonify({"status": "error", "message": "Loan application not found."}), 404

        customer = Customer.query.get(offer.customer_id)
        if not customer:
            current_app.logger.error(f"Status update failed: Customer {offer.customer_id} not found for offer {offer.offer_id}.")
            return jsonify({"status": "error", "message": "Associated customer not found."}), 404

        # Log the application stage event
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type=f'APP_STAGE_{application_stage.upper().replace(" ", "_")}', # e.g., APP_STAGE_LOGIN, APP_STAGE_BUREAU_CHECK
            event_source='LOS' if 'LOS' in request.url_rule.rule else 'E-aggregator', # Infer source, adjust as needed
            event_timestamp=event_timestamp,
            event_details={
                "loan_application_number": loan_application_number,
                "stage_details": status_details,
                "current_offer_id": str(offer.offer_id)
            }
        )
        db.session.add(event)

        # Update offer status if the application stage implies a final state (e.g., 'Rejected', 'Approved')
        # FR13: Prevent modification of customer offers with started loan application journeys until expired/rejected.
        # FR38: Mark offers as expired if LAN validity post journey start date is over.
        # This is a simplified update; more complex logic for FR13/FR38 would likely be in a dedicated service/job.
        if application_stage.lower() in ['rejected', 'approved', 'disbursed', 'cancelled', 'expired']:
            offer.offer_status = application_stage.capitalize()
            offer.updated_at = datetime.now()
            db.session.add(offer)
            current_app.logger.info(f"Offer {offer.offer_id} status updated to '{application_stage}'.")

        db.session.commit()
        current_app.logger.info(f"Application status event '{application_stage}' logged for loan {loan_application_number}.")

        return jsonify({"status": "success", "message": "Status updated"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during status update: {e}")
        return jsonify({"status": "error", "message": "Internal server error during database operation."}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error during status update: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500