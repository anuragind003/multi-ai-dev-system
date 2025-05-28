import os
import uuid
import base64
import io
import pandas as pd
from datetime import datetime, date, timedelta

from flask import Flask, request, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text, func, or_
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@db:5432/cdp_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')

db = SQLAlchemy(app)

# --- Database Models ---

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    pan = db.Column(db.String(10), unique=True)
    aadhaar_ref_number = db.Column(db.String(12), unique=True)
    ucid = db.Column(db.String(50), unique=True)
    previous_loan_app_number = db.Column(db.String(50), unique=True)
    customer_attributes = db.Column(JSONB)
    customer_segment = db.Column(db.String(10))
    is_dnd = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    offers = db.relationship('Offer', backref='customer', lazy=True)
    events = db.relationship('CustomerEvent', backref='customer', lazy=True)

    def __repr__(self):
        return f"<Customer {self.mobile_number}>"

class Offer(db.Model):
    __tablename__ = 'offers'
    offer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.String(20)) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.String(20)) # 'Active', 'Inactive', 'Expired', 'Converted'
    propensity_flag = db.Column(db.String(50)) # e.g., 'dominant tradeline'
    offer_start_date = db.Column(db.Date)
    offer_end_date = db.Column(db.Date)
    loan_application_number = db.Column(db.String(50)) # Nullable, if journey not started
    attribution_channel = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Offer {self.offer_id} for Customer {self.customer_id}>"

class CustomerEvent(db.Model):
    __tablename__ = 'customer_events'
    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False) # 'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICK', 'CONVERSION', 'APP_STAGE_LOGIN', etc.
    event_source = db.Column(db.String(20), nullable=False) # 'Moengage', 'LOS', 'API'
    event_timestamp = db.Column(db.DateTime(timezone=True), default=datetime.now)
    event_details = db.Column(JSONB) # Stores specific event data (e.g., application stage details)

    def __repr__(self):
        return f"<CustomerEvent {self.event_type} at {self.event_timestamp}>"

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    campaign_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_unique_identifier = db.Column(db.String(100), unique=True, nullable=False)
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_date = db.Column(db.Date)
    targeted_customers_count = db.Column(db.Integer)
    attempted_count = db.Column(db.Integer)
    successfully_sent_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    success_rate = db.Column(db.Numeric(5,2))
    conversion_rate = db.Column(db.Numeric(5,2))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Campaign {self.campaign_name} ({self.campaign_unique_identifier})>"

class DataIngestionLog(db.Model):
    __tablename__ = 'data_ingestion_logs'
    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = db.Column(db.String(255), nullable=False)
    upload_timestamp = db.Column(db.DateTime(timezone=True), default=datetime.now)
    status = db.Column(db.String(20), nullable=False) # 'SUCCESS', 'FAILED', 'PARTIAL'
    error_details = db.Column(db.Text) # Stores error messages for failed records (e.g., JSON string)
    uploaded_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<DataIngestionLog {self.file_name} - {self.status}>"

# --- Helper/Service functions (simplified for this file, would typically be in app.services) ---
# These are mock implementations to satisfy the API endpoints.
# Real logic would involve complex data processing, validation, deduplication, etc.

def _perform_deduplication(customer_data: dict) -> Customer:
    """
    Simulates deduplication logic (FR2, FR3, FR4, FR5).
    Queries the DB for existing customers based on mobile, PAN, Aadhaar, UCID,
    or previous loan application number.
    Returns the existing Customer object or None if no match.
    """
    query_filters = []
    if customer_data.get('mobile_number'):
        query_filters.append(Customer.mobile_number == customer_data['mobile_number'])
    if customer_data.get('pan'):
        query_filters.append(Customer.pan == customer_data['pan'])
    if customer_data.get('aadhaar_ref_number'):
        query_filters.append(Customer.aadhaar_ref_number == customer_data['aadhaar_ref_number'])
    if customer_data.get('ucid'):
        query_filters.append(Customer.ucid == customer_data['ucid'])
    if customer_data.get('previous_loan_app_number'):
        query_filters.append(Customer.previous_loan_app_number == customer_data['previous_loan_app_number'])

    if not query_filters:
        return None # No identifiable data for deduplication

    existing_customer = Customer.query.filter(or_(*query_filters)).first()
    return existing_customer

def _validate_customer_data(data: dict) -> tuple[bool, str]:
    """Basic column-level validation (FR1, NFR2)."""
    if not data.get('mobile_number'):
        return False, "Mobile number is required."
    # Add more validation rules as per FR1 (e.g., PAN length, Aadhaar format)
    if data.get('pan') and len(data['pan']) != 10:
        return False, "PAN must be 10 characters long."
    return True, "Validation successful."

def _generate_moengage_file_content() -> bytes:
    """
    Generates mock Moengage file content (CSV).
    FR25, FR39: Download Moengage File.
    In a real scenario, this would query the database for relevant customer and campaign data,
    apply DND checks (FR21), and format it as per Moengage requirements.
    """
    # Example: Fetch active customers not marked as DND with active offers
    customers_for_moengage = Customer.query.filter(
        Customer.is_dnd == False,
        Customer.offers.any(Offer.offer_status == 'Active')
    ).limit(100).all() # Limit for mock data

    moengage_records = []
    for customer in customers_for_moengage:
        # Simplified: pick one active offer
        active_offer = next((o for o in customer.offers if o.offer_status == 'Active'), None)
        if active_offer:
            moengage_records.append({
                "customer_id": str(customer.customer_id),
                "mobile": customer.mobile_number,
                "pan": customer.pan,
                "offer_id": str(active_offer.offer_id),
                "offer_amount": "100000", # Mock value
                "campaign_id": "CMP_MOCK_001", # Mock value
                "offer_type": active_offer.offer_type,
                "customer_segment": customer.customer_segment
            })
    
    if not moengage_records:
        # If no real data, provide a dummy record to show format
        moengage_records.append({
            "customer_id": "dummy_id_1", "mobile": "9999999999", "pan": "ABCDE1234F",
            "offer_id": "dummy_offer_1", "offer_amount": "50000", "campaign_id": "DUMMY_CMP",
            "offer_type": "Fresh", "customer_segment": "C1"
        })

    df = pd.DataFrame(moengage_records)
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode('utf-8')

def _get_duplicate_data_content() -> bytes:
    """
    Generates mock duplicate data file content (CSV).
    FR26: Download Duplicate Data File.
    In a real scenario, this would query the database for identified duplicate records
    based on the deduplication logic, possibly from a dedicated 'duplicates' table
    or by analyzing customer data with multiple matches.
    """
    mock_data = [
        {"mobile_number": "9876543210", "pan": "ABCDE1234F", "duplicate_reason": "Mobile and PAN match", "original_customer_id": str(uuid.uuid4())},
        {"mobile_number": "9988776655", "aadhaar": "123456789012", "duplicate_reason": "Aadhaar match", "original_customer_id": str(uuid.uuid4())},
    ]
    df = pd.DataFrame(mock_data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode('utf-8')

def _get_unique_data_content() -> bytes:
    """
    Generates mock unique data file content (CSV).
    FR27: Download Unique Data File.
    In a real scenario, this would query the database for unique customer profiles
    after deduplication.
    """
    unique_customers = Customer.query.limit(100).all() # Fetch some unique customers
    unique_records = []
    for customer in unique_customers:
        unique_records.append({
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan": customer.pan,
            "customer_segment": customer.customer_segment,
            "is_dnd": customer.is_dnd
        })
    
    if not unique_records:
        unique_records.append({
            "customer_id": str(uuid.uuid4()), "mobile_number": "1111111111", "pan": "UNIQUE1234",
            "customer_segment": "C1", "is_dnd": False
        })

    df = pd.DataFrame(unique_records)
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode('utf-8')

def _get_error_data_content(log_id: str) -> bytes:
    """
    Generates error data file content (Excel) from a specific log entry.
    FR28, FR32: Download Error Excel file.
    """
    log_entry = DataIngestionLog.query.get(log_id)
    if not log_entry or log_entry.status == 'SUCCESS' or not log_entry.error_details:
        return None

    # Assuming error_details is stored as JSON string of records
    error_records = pd.read_json(io.StringIO(log_entry.error_details), orient='records')
    output = io.BytesIO()
    error_records.to_excel(output, index=False, engine='xlsxwriter')
    output.seek(0)
    return output.getvalue()

def _get_daily_tally_report_data() -> dict:
    """
    Generates mock daily tally report data.
    FR35: Front-end for daily reports for data tally.
    In a real scenario, this would aggregate data from various tables
    for the current day or a specified period.
    """
    today = date.today()
    total_customers = db.session.query(func.count(Customer.customer_id)).scalar()
    new_customers_today = db.session.query(func.count(Customer.customer_id)).filter(
        func.date(Customer.created_at) == today
    ).scalar()
    new_offers_today = db.session.query(func.count(Offer.offer_id)).filter(
        func.date(Offer.created_at) == today
    ).scalar()
    total_events_today = db.session.query(func.count(CustomerEvent.event_id)).filter(
        func.date(CustomerEvent.event_timestamp) == today
    ).scalar()
    successful_uploads_today = db.session.query(func.count(DataIngestionLog.log_id)).filter(
        func.date(DataIngestionLog.upload_timestamp) == today,
        DataIngestionLog.status == 'SUCCESS'
    ).scalar()
    failed_uploads_today = db.session.query(func.count(DataIngestionLog.log_id)).filter(
        func.date(DataIngestionLog.upload_timestamp) == today,
        DataIngestionLog.status == 'FAILED'
    ).scalar()

    return {
        "date": today.strftime('%Y-%m-%d'),
        "total_customers_in_cdp": total_customers,
        "new_customers_today": new_customers_today,
        "new_offers_generated_today": new_offers_today,
        "total_events_tracked_today": total_events_today,
        "successful_file_uploads_today": successful_uploads_today,
        "failed_file_uploads_today": failed_uploads_today,
        "deduplicated_customers_today": "N/A (complex to calculate in mock)"
    }

def _get_customer_profile_view(customer_id: uuid.UUID) -> dict:
    """
    Retrieves a single customer's profile view with associated offers and application stages.
    FR2, FR36: Single profile view, customer level view with stages.
    """
    customer = Customer.query.get(customer_id)
    if not customer:
        return None

    offers_data = []
    for offer in customer.offers:
        offers_data.append({
            "offer_id": str(offer.offer_id),
            "offer_type": offer.offer_type,
            "offer_status": offer.offer_status,
            "propensity_flag": offer.propensity_flag,
            "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
            "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
            "loan_application_number": offer.loan_application_number,
            "attribution_channel": offer.attribution_channel,
            "created_at": offer.created_at.isoformat()
        })

    events_data = []
    for event in customer.events:
        events_data.append({
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "event_source": event.event_source,
            "event_timestamp": event.event_timestamp.isoformat(),
            "event_details": event.event_details
        })

    # Filter offer history for past 6 months (FR18)
    six_months_ago = datetime.now() - timedelta(days=6*30) # Approx 6 months
    offer_history_6m = [o for o in offers_data if datetime.fromisoformat(o['created_at']) >= six_months_ago]

    return {
        "customer_id": str(customer.customer_id),
        "mobile_number": customer.mobile_number,
        "pan": customer.pan,
        "aadhaar_ref_number": customer.aadhaar_ref_number,
        "ucid": customer.ucid,
        "previous_loan_app_number": customer.previous_loan_app_number,
        "customer_attributes": customer.customer_attributes,
        "customer_segment": customer.customer_segment,
        "is_dnd": customer.is_dnd,
        "active_offers": [o for o in offers_data if o['offer_status'] == 'Active'],
        "offer_history_6_months": offer_history_6m,
        "application_stages": [e for e in events_data if e['event_type'].startswith('APP_STAGE_')], # FR22
        "all_events": events_data
    }

def process_customer_upload_file(file_content_bytes: bytes, file_type: str, uploaded_by: str) -> dict:
    """
    Processes the uploaded customer details file.
    This function simulates the complex logic of validation, deduplication,
    lead generation, and tracking success/failure.
    FR29, FR30, FR31, FR32
    """
    log_id = uuid.uuid4()
    file_name = f"{file_type}_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    success_count = 0
    error_records = []
    total_records = 0

    try:
        df = pd.read_csv(io.BytesIO(file_content_bytes))
        total_records = len(df)

        for index, row in df.iterrows():
            customer_data = {
                "mobile_number": str(row.get('mobile_number')) if pd.notna(row.get('mobile_number')) else None,
                "pan": str(row.get('pan')) if pd.notna(row.get('pan')) else None,
                "aadhaar_ref_number": str(row.get('aadhaar_ref_number')) if pd.notna(row.get('aadhaar_ref_number')) else None,
                "ucid": str(row.get('ucid')) if pd.notna(row.get('ucid')) else None,
                "previous_loan_app_number": str(row.get('previous_loan_app_number')) if pd.notna(row.get('previous_loan_app_number')) else None,
                "customer_segment": str(row.get('customer_segment')) if pd.notna(row.get('customer_segment')) else None,
                "customer_attributes": row.to_dict() # Store all row data as attributes for simplicity
            }

            is_valid, validation_msg = _validate_customer_data(customer_data)
            if not is_valid:
                error_records.append({"row_number": index + 1, "error_desc": validation_msg, **customer_data})
                continue

            try:
                existing_customer = _perform_deduplication(customer_data)
                if existing_customer:
                    customer = existing_customer
                    # Update existing customer details if necessary (e.g., segment, attributes)
                    customer.customer_segment = customer_data.get('customer_segment') or customer.customer_segment
                    customer.customer_attributes = customer_data.get('customer_attributes') or customer.customer_attributes
                    customer.updated_at = datetime.now()
                else:
                    customer = Customer(**{k: v for k, v in customer_data.items() if v is not None}) # Filter out None values for new customer
                    db.session.add(customer)
                db.session.commit() # Commit each customer for atomicity in case of large files

                # Simulate lead generation (FR30)
                # In a real system, this might trigger an external API call or a more complex internal process
                app.logger.info(f"Lead generated/updated for customer: {customer.customer_id}")
                success_count += 1

            except IntegrityError as e:
                db.session.rollback()
                error_records.append({"row_number": index + 1, "error_desc": f"Duplicate entry or data integrity error: {e.orig.diag.message_detail if hasattr(e.orig, 'diag') else e}", **customer_data})
            except SQLAlchemyError as e:
                db.session.rollback()
                error_records.append({"row_number": index + 1, "error_desc": f"Database error: {e}", **customer_data})
            except Exception as e:
                db.session.rollback()
                error_records.append({"row_number": index + 1, "error_desc": f"Unexpected error: {e}", **customer_data})

        status = "SUCCESS" if not error_records else ("PARTIAL" if success_count > 0 else "FAILED")
        error_details = pd.DataFrame(error_records).to_json(orient='records') if error_records else None

        log_entry = DataIngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status=status,
            error_details=error_details,
            uploaded_by=uploaded_by
        )
        db.session.add(log_entry)
        db.session.commit()

        return {
            "status": status,
            "message": f"File processed. Total: {total_records}, Success: {success_count}, Failed: {len(error_records)}",
            "log_id": str(log_id),
            "error_file_available": bool(error_records)
        }

    except Exception as e:
        db.session.rollback()
        log_entry = DataIngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status="FAILED",
            error_details=f"File parsing or general processing error: {e}",
            uploaded_by=uploaded_by
        )
        db.session.add(log_entry)
        db.session.commit()
        app.logger.error(f"Error in process_customer_upload_file: {e}")
        return {
            "status": "FAILED",
            "message": f"Failed to process file: {e}",
            "log_id": str(log_id),
            "error_file_available": True
        }

# --- API Endpoints ---

# Lead/Eligibility/Status APIs (FR9, FR10)
@app.route('/api/leads', methods=['POST'])
def create_lead():
    """
    Receives real-time lead generation data from Insta/E-aggregators and inserts into CDP.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    is_valid, validation_msg = _validate_customer_data(data)
    if not is_valid:
        return jsonify({"status": "error", "message": validation_msg}), 400

    try:
        customer_data = {
            "mobile_number": data.get('mobile_number'),
            "pan": data.get('pan'),
            "aadhaar_ref_number": data.get('aadhaar_ref_number'),
            "ucid": data.get('ucid'),
            "previous_loan_app_number": data.get('application_id'), # Mapping application_id to previous_loan_app_number for new leads
            "customer_attributes": data # Store all incoming data as attributes
        }
        existing_customer = _perform_deduplication(customer_data)

        if existing_customer:
            customer = existing_customer
            # Update existing customer details if necessary
            customer.updated_at = datetime.now()
        else:
            customer = Customer(**{k: v for k, v in customer_data.items() if v is not None})
            db.session.add(customer)

        db.session.commit()

        # Log the event (FR21)
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type="LEAD_GENERATED",
            event_source=data.get('source_channel', 'API'),
            event_details=data
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
        return jsonify({"status": "error", "message": f"Data integrity error: {e.orig.diag.message_detail if hasattr(e.orig, 'diag') else e}"}), 409
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Database error during lead creation: {e}")
        return jsonify({"status": "error", "message": "Database error during lead processing"}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error during lead creation: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500

@app.route('/api/eligibility', methods=['POST'])
def update_eligibility():
    """
    Receives real-time eligibility check data from Insta/E-aggregators and inserts into CDP.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    mobile_number = data.get('mobile_number')
    loan_application_number = data.get('loan_application_number')
    eligibility_status = data.get('eligibility_status')
    offer_id = data.get('offer_id')

    if not mobile_number or not eligibility_status:
        return jsonify({"status": "error", "message": "mobile_number and eligibility_status are required"}), 400

    try:
        customer = Customer.query.filter_by(mobile_number=mobile_number).first()

        if not customer:
            # If customer doesn't exist, create a minimal one or return error based on business rule
            # For now, create a new customer if mobile number is provided
            customer = Customer(mobile_number=mobile_number, customer_attributes=data)
            db.session.add(customer)
            db.session.commit() # Commit to get customer_id for event logging

        # Log the event (FR21)
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type="ELIGIBILITY_CHECK",
            event_source=data.get('source_channel', 'API'),
            event_details=data
        )
        db.session.add(event)

        # Update offer status or create new offer if applicable (FR15)
        if offer_id:
            offer = Offer.query.get(offer_id)
            if offer and offer.customer_id == customer.customer_id:
                offer.offer_status = eligibility_status # Or map to 'Active', 'Inactive'
                offer.updated_at = datetime.now()
        # Else, if it's a new eligibility for a customer without a specific offer_id,
        # a new offer might be created or an existing one updated based on business logic.
        # For simplicity, we'll just log the event for now.

        db.session.commit()
        return jsonify({"status": "success", "message": "Eligibility data processed"}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Database error during eligibility update: {e}")
        return jsonify({"status": "error", "message": "Database error during eligibility processing"}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error during eligibility update: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500

@app.route('/api/status', methods=['POST'])
def update_application_status():
    """
    Receives real-time loan application status updates from Insta/E-aggregators and inserts into CDP.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    loan_application_number = data.get('loan_application_number')
    application_stage = data.get('application_stage')
    status_details = data.get('status_details')
    event_timestamp_str = data.get('event_timestamp')

    if not loan_application_number or not application_stage:
        return jsonify({"status": "error", "message": "loan_application_number and application_stage are required"}), 400

    try:
        event_timestamp = datetime.fromisoformat(event_timestamp_str) if event_timestamp_str else datetime.now()

        # Find customer associated with the loan_application_number
        # This might involve looking up in Offers table or directly in Customer if LAN is a primary identifier
        offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()
        customer = None
        if offer:
            customer = offer.customer
        else:
            # Try to find customer by previous_loan_app_number if it's a new application
            customer = Customer.query.filter_by(previous_loan_app_number=loan_application_number).first()

        if not customer:
            # If customer not found, create a minimal customer and offer record
            # This handles cases where the application journey starts without a prior lead/offer
            customer = Customer(mobile_number=f"UNKNOWN_{loan_application_number}", previous_loan_app_number=loan_application_number, customer_attributes={"source": "status_api_new_customer"})
            db.session.add(customer)
            db.session.flush() # Assign customer_id before committing

            offer = Offer(
                customer_id=customer.customer_id,
                loan_application_number=loan_application_number,
                offer_status='Journey Started', # Initial status for new offer from status API
                offer_type='New-new', # Assuming new journey
                created_at=event_timestamp
            )
            db.session.add(offer)
            db.session.commit() # Commit to ensure customer and offer exist for event logging
            app.logger.info(f"Created new customer and offer for unknown LAN: {loan_application_number}")


        # Log the event (FR21, FR22)
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type=f"APP_STAGE_{application_stage.upper()}", # e.g., APP_STAGE_LOGIN
            event_source=data.get('source_channel', 'LOS'), # Assuming LOS for application stages
            event_timestamp=event_timestamp,
            event_details=status_details
        )
        db.session.add(event)

        # Update offer status based on application journey (FR13, FR38)
        if offer: # If an offer was found or created
            if application_stage.lower() in ['e-sign', 'conversion']:
                offer.offer_status = 'Converted'
            elif application_stage.lower() in ['rejected', 'expired']:
                offer.offer_status = 'Expired'
            offer.updated_at = datetime.now()

        db.session.commit()
        return jsonify({"status": "success", "message": "Status updated"}), 200
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid event_timestamp format. Use ISO format."}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"Database error during status update: {e}")
        return jsonify({"status": "error", "message": "Database error during status processing"}), 500
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error during status update: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500

# Admin Portal Endpoints (FR29-FR32)
@app.route('/api/admin/upload/customer-details', methods=['POST'])
def upload_customer_details():
    """
    Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans) for lead generation via Admin Portal.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    file_type = data.get('file_type')
    file_content_base64 = data.get('file_content_base64')
    uploaded_by = data.get('uploaded_by', 'Admin')

    if not file_type or not file_content_base64:
        return jsonify({"status": "error", "message": "file_type and file_content_base64 are required"}), 400

    try:
        file_content_bytes = base64.b64decode(file_content_base64)
        result = process_customer_upload_file(file_content_bytes, file_type, uploaded_by)
        status_code = 200 if result['status'] in ['SUCCESS', 'PARTIAL'] else 400
        return jsonify(result), status_code
    except Exception as e:
        app.logger.error(f"Error processing file upload: {e}")
        return jsonify({"status": "error", "message": f"Failed to decode or process file: {e}"}), 400

# Reporting Endpoints (FR25-FR28, FR35, FR36, FR39)
@app.route('/api/reports/moengage-file', methods=['GET'])
def download_moengage_file():
    """
    Downloads the Moengage format file in CSV for campaign uploads.
    """
    try:
        csv_data = _generate_moengage_file_content()
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = "attachment; filename=moengage_campaign_data.csv"
        response.headers["Content-Type"] = "text/csv"
        return response
    except Exception as e:
        app.logger.error(f"Error generating Moengage file: {e}")
        return jsonify({"status": "error", "message": "Failed to generate Moengage file"}), 500

@app.route('/api/reports/duplicate-data', methods=['GET'])
def download_duplicate_data():
    """
    Downloads the Duplicate Data File in CSV/Excel format.
    """
    file_format = request.args.get('format', 'csv').lower() # Default to CSV
    try:
        if file_format == 'csv':
            csv_data = _get_duplicate_data_content()
            response = make_response(csv_data)
            response.headers["Content-Disposition"] = "attachment; filename=duplicate_customer_data.csv"
            response.headers["Content-Type"] = "text/csv"
            return response
        elif file_format == 'excel':
            # Re-use CSV content generation and convert to Excel using pandas
            csv_data = _get_duplicate_data_content()
            df = pd.read_csv(io.BytesIO(csv_data))
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='xlsxwriter')
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = "attachment; filename=duplicate_customer_data.xlsx"
            response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return response
        else:
            return jsonify({"status": "error", "message": "Unsupported format. Choose 'csv' or 'excel'."}), 400
    except Exception as e:
        app.logger.error(f"Error generating duplicate data file: {e}")
        return jsonify({"status": "error", "message": "Failed to generate duplicate data file"}), 500

@app.route('/api/reports/unique-data', methods=['GET'])
def download_unique_data():
    """
    Downloads the Unique Data File in CSV/Excel format.
    """
    file_format = request.args.get('format', 'csv').lower() # Default to CSV
    try:
        if file_format == 'csv':
            csv_data = _get_unique_data_content()
            response = make_response(csv_data)
            response.headers["Content-Disposition"] = "attachment; filename=unique_customer_data.csv"
            response.headers["Content-Type"] = "text/csv"
            return response
        elif file_format == 'excel':
            # Re-use CSV content generation and convert to Excel using pandas
            csv_data = _get_unique_data_content()
            df = pd.read_csv(io.BytesIO(csv_data))
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='xlsxwriter')
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers["Content-Disposition"] = "attachment; filename=unique_customer_data.xlsx"
            response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return response
        else:
            return jsonify({"status": "error", "message": "Unsupported format. Choose 'csv' or 'excel'."}), 400
    except Exception as e:
        app.logger.error(f"Error generating unique data file: {e}")
        return jsonify({"status": "error", "message": "Failed to generate unique data file"}), 500

@app.route('/api/reports/error-data', methods=['GET'])
def download_error_data():
    """
    Downloads the Error Excel file for failed data uploads.
    """
    log_id = request.args.get('log_id')
    if not log_id:
        return jsonify({"status": "error", "message": "log_id is required to download error file."}), 400

    try:
        excel_data = _get_error_data_content(log_id)
        if excel_data is None:
            return jsonify({"status": "error", "message": "No error data found for this log ID or log status is SUCCESS."}), 404

        response = make_response(excel_data)
        response.headers["Content-Disposition"] = f"attachment; filename=error_log_{log_id}.xlsx"
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    except Exception as e:
        app.logger.error(f"Error generating error data file for log_id {log_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to generate error data file"}), 500

@app.route('/api/reports/daily-tally', methods=['GET'])
def get_daily_tally():
    """
    Retrieves daily data tally reports for frontend display.
    """
    try:
        report_data = _get_daily_tally_report_data()
        return jsonify({"status": "success", "data": report_data}), 200
    except Exception as e:
        app.logger.error(f"Error retrieving daily tally report: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve daily tally report"}), 500

@app.route('/api/customer/<uuid:customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    """
    Retrieves a single customer's profile view with associated offers and application stages.
    """
    try:
        customer_profile = _get_customer_profile_view(customer_id)
        if not customer_profile:
            return jsonify({"status": "error", "message": "Customer not found"}), 404
        return jsonify({"status": "success", "data": customer_profile}), 200
    except Exception as e:
        app.logger.error(f"Error retrieving customer profile for {customer_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to retrieve customer profile"}), 500

# --- Database Initialization (for development/testing) ---
@app.cli.command('create-db')
def create_db_command():
    """Creates the database tables."""
    with app.app_context():
        db.create_all()
    print('Database tables created.')

@app.cli.command('drop-db')
def drop_db_command():
    """Drops the database tables."""
    with app.app_context():
        db.drop_all()
    print('Database tables dropped.')

if __name__ == '__main__':
    # This block is for local development only.
    # In production, a WSGI server (like Gunicorn) would run the app.
    with app.app_context():
        # Ensure tables exist on startup for dev, or use 'flask create-db'
        # db.create_all()
        pass
    app.run(debug=True, host='0.0.0.0', port=5000)