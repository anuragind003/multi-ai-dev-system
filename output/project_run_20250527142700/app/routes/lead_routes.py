from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import uuid
import base64
import io
import pandas as pd # Assuming pandas for file processing simulation

lead_bp = Blueprint('lead_routes', __name__)

@lead_bp.route('/api/leads', methods=['POST'])
def create_lead():
    """
    Receives real-time lead generation data from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    mobile_number = data.get('mobile_number')
    pan = data.get('pan')
    loan_type = data.get('loan_type')
    source_channel = data.get('source_channel')
    application_id = data.get('application_id') # This might be a temporary ID before LAN

    if not mobile_number:
        return jsonify({"status": "error", "message": "Mobile number is required"}), 400

    try:
        # FR2, FR3, FR4: Deduplication logic (simplified for this route, full logic in a service)
        customer = Customer.query.filter(
            (Customer.mobile_number == mobile_number) |
            (Customer.pan == pan if pan else False) |
            (Customer.aadhaar_ref_number == data.get('aadhaar_ref_number') if data.get('aadhaar_ref_number') else False) |
            (Customer.ucid == data.get('ucid') if data.get('ucid') else False) |
            (Customer.previous_loan_app_number == data.get('previous_loan_app_number') if data.get('previous_loan_app_number') else False)
        ).first()

        if customer:
            # Update existing customer attributes if new data is richer
            if pan and not customer.pan:
                customer.pan = pan
            if data.get('aadhaar_ref_number') and not customer.aadhaar_ref_number:
                customer.aadhaar_ref_number = data.get('aadhaar_ref_number')
            if data.get('ucid') and not customer.ucid:
                customer.ucid = data.get('ucid')
            if data.get('previous_loan_app_number') and not customer.previous_loan_app_number:
                customer.previous_loan_app_number = data.get('previous_loan_app_number')
            customer.updated_at = db.func.current_timestamp()
            db.session.add(customer)
        else:
            customer = Customer(
                mobile_number=mobile_number,
                pan=pan,
                aadhaar_ref_number=data.get('aadhaar_ref_number'),
                ucid=data.get('ucid'),
                previous_loan_app_number=data.get('previous_loan_app_number'),
                customer_attributes=data.get('customer_attributes', {})
            )
            db.session.add(customer)

        db.session.flush() # To get customer.customer_id before commit

        # Create a lead generation event
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type='LEAD_GENERATED',
            event_source=source_channel or 'API',
            event_details={
                "loan_type": loan_type,
                "application_id": application_id,
                "source_channel": source_channel
            }
        )
        db.session.add(event)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Lead processed successfully",
            "customer_id": str(customer.customer_id)
        }), 200

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Data integrity error: {str(e)}"}), 409
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

@lead_bp.route('/api/eligibility', methods=['POST'])
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
    loan_application_number = data.get('loan_application_number')
    eligibility_status = data.get('eligibility_status')
    offer_id = data.get('offer_id')
    source_channel = data.get('source_channel')

    if not mobile_number or not eligibility_status:
        return jsonify({"status": "error", "message": "Mobile number and eligibility status are required"}), 400

    try:
        customer = Customer.query.filter_by(mobile_number=mobile_number).first()
        if not customer:
            return jsonify({"status": "error", "message": "Customer not found"}), 404

        # Find or create offer based on offer_id or loan_application_number
        offer = None
        if offer_id:
            offer = Offer.query.get(offer_id)
        elif loan_application_number:
            offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()

        if not offer:
            # If no existing offer, create a new one (e.g., for a fresh eligibility check)
            offer = Offer(
                customer_id=customer.customer_id,
                offer_type='Fresh', # Default, can be refined
                offer_status='Active', # Default, can be refined
                loan_application_number=loan_application_number,
                attribution_channel=source_channel
            )
            db.session.add(offer)
            db.session.flush() # To get offer.offer_id

        # Update offer status based on eligibility
        if eligibility_status.lower() == 'eligible':
            offer.offer_status = 'Active'
        elif eligibility_status.lower() == 'not_eligible':
            offer.offer_status = 'Inactive' # Or 'Rejected'
        offer.updated_at = db.func.current_timestamp()
        db.session.add(offer)

        # Create an eligibility event
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type='ELIGIBILITY_CHECK',
            event_source=source_channel or 'API',
            event_details={
                "eligibility_status": eligibility_status,
                "loan_application_number": loan_application_number,
                "offer_id": str(offer.offer_id) if offer else None
            }
        )
        db.session.add(event)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Eligibility data processed",
            "customer_id": str(customer.customer_id),
            "offer_id": str(offer.offer_id) if offer else None
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

@lead_bp.route('/api/status', methods=['POST'])
def update_application_status():
    """
    Receives real-time loan application status updates from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Status API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    FR22: Event data shall include SMS sent, SMS delivered, SMS click (from Moengage), conversions (from LOS/Moengage), and application stages (login, bureau check, offer details, eKYC, Bank details, other details, e-sign) (from LOS).
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    loan_application_number = data.get('loan_application_number')
    application_stage = data.get('application_stage')
    status_details = data.get('status_details')
    event_timestamp = data.get('event_timestamp') # Optional, use current_timestamp if not provided
    event_source = data.get('event_source', 'LOS') # Default to LOS as per FR22

    if not loan_application_number or not application_stage:
        return jsonify({"status": "error", "message": "Loan application number and application stage are required"}), 400

    try:
        offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()
        if not offer:
            return jsonify({"status": "error", "message": "Offer/Loan Application not found"}), 404

        customer = Customer.query.get(offer.customer_id)
        if not customer:
            return jsonify({"status": "error", "message": "Associated customer not found"}), 404

        # Update offer status based on application stage (simplified)
        if application_stage.lower() in ['e-sign', 'conversion']:
            offer.offer_status = 'Converted'
        elif application_stage.lower() in ['rejected', 'expired']:
            offer.offer_status = application_stage.capitalize() # FR13, FR38
        else:
            offer.offer_status = 'Journey Started' # Or a more granular status
        offer.updated_at = db.func.current_timestamp()
        db.session.add(offer)

        # Create an application stage event
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type=f'APP_STAGE_{application_stage.upper().replace(" ", "_")}',
            event_source=event_source,
            event_timestamp=event_timestamp,
            event_details={
                "loan_application_number": loan_application_number,
                "status_details": status_details,
                "current_offer_status": offer.offer_status
            }
        )
        db.session.add(event)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Status updated",
            "customer_id": str(customer.customer_id),
            "offer_id": str(offer.offer_id)
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

@lead_bp.route('/api/admin/upload/customer-details', methods=['POST'])
def upload_customer_details():
    """
    Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans) for lead generation via Admin Portal.
    FR29: The Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.
    FR30: The Admin Portal shall generate a lead for customers in the system upon successful file upload.
    FR31: The Admin Portal shall generate a success file upon successful upload of all data.
    FR32: The Admin Portal shall generate an error file with an 'Error Desc' column for failed uploads.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    file_type = data.get('file_type')
    file_content_base64 = data.get('file_content_base64')
    uploaded_by = data.get('uploaded_by')

    if not file_type or not file_content_base64 or not uploaded_by:
        return jsonify({"status": "error", "message": "File type, file content, and uploader are required"}), 400

    log_id = uuid.uuid4()
    file_name = f"{file_type}_upload_{log_id}.csv" # Assuming CSV for simplicity

    try:
        # Decode base64 content
        decoded_content = base64.b64decode(file_content_base64)
        # For a real system, this would trigger a background task (e.g., Celery)
        # to process the file, perform validation, deduplication, and lead generation.
        # Here, we simulate the initiation and log the request.

        # Simulate file processing (e.g., read with pandas)
        # In a real scenario, this would be in a separate worker/service
        # For demonstration, we'll just check if it's readable.
        try:
            # Assuming CSV content for simplicity
            df = pd.read_csv(io.StringIO(decoded_content.decode('utf-8')))
            # Basic check for expected columns, e.g., 'mobile_number'
            if 'mobile_number' not in df.columns:
                raise ValueError("File must contain 'mobile_number' column.")
            processing_status = "SUCCESS"
            error_details = None
            message = "File uploaded, processing initiated successfully."
        except Exception as e:
            processing_status = "FAILED"
            error_details = f"File parsing or initial validation failed: {str(e)}"
            message = "File upload failed due to content issues."

        # Log the ingestion request
        ingestion_log = DataIngestionLog(
            log_id=log_id,
            file_name=file_name,
            status=processing_status,
            error_details=error_details,
            uploaded_by=uploaded_by
        )
        db.session.add(ingestion_log)
        db.session.commit()

        if processing_status == "FAILED":
            return jsonify({
                "status": "error",
                "message": message,
                "log_id": str(log_id),
                "error_details": error_details
            }), 400
        else:
            return jsonify({
                "status": "success",
                "message": message,
                "log_id": str(log_id)
            }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Database error during logging: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"An unexpected error occurred during file upload: {str(e)}"}), 500

# Note: Actual file processing (deduplication, lead generation, success/error file creation)
# would be handled by a separate background task (e.g., Celery worker) triggered by this upload.
# The `log_id` can be used to track the status of that background job.