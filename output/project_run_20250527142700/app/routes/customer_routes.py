from flask import Blueprint, request, jsonify, send_file, abort
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Date, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import os
import io
import base64
import uuid
from datetime import datetime, date

# --- Database Configuration ---
# In a real application, these would come from a config file or environment variables
# Ensure 'db' is the service name for your PostgreSQL container if running in Docker Compose
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/cdp_db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# --- Database Models ---
class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True, nullable=False)
    pan = Column(String(10), unique=True)
    aadhaar_ref_number = Column(String(12), unique=True)
    ucid = Column(String(50), unique=True)
    previous_loan_app_number = Column(String(50), unique=True)
    customer_attributes = Column(JSONB) # Stores various customer attributes
    customer_segment = Column(String(10)) # e.g., C1 to C8
    is_dnd = Column(Boolean, default=False) # Flag for Do Not Disturb customers
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "customer_id": str(self.customer_id),
            "mobile_number": self.mobile_number,
            "pan": self.pan,
            "aadhaar_ref_number": self.aadhaar_ref_number,
            "ucid": self.ucid,
            "previous_loan_app_number": self.previous_loan_app_number,
            "customer_attributes": self.customer_attributes,
            "customer_segment": self.customer_segment,
            "is_dnd": self.is_dnd,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Offer(Base):
    __tablename__ = 'offers'
    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    offer_type = Column(String(20)) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = Column(String(20)) # 'Active', 'Inactive', 'Expired'
    propensity_flag = Column(String(50)) # e.g., 'dominant tradeline'
    offer_start_date = Column(Date)
    offer_end_date = Column(Date)
    loan_application_number = Column(String(50)) # Nullable, if journey not started
    attribution_channel = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "offer_id": str(self.offer_id),
            "customer_id": str(self.customer_id),
            "offer_type": self.offer_type,
            "offer_status": self.offer_status,
            "propensity_flag": self.propensity_flag,
            "offer_start_date": self.offer_start_date.isoformat() if self.offer_start_date else None,
            "offer_end_date": self.offer_end_date.isoformat() if self.offer_end_date else None,
            "loan_application_number": self.loan_application_number,
            "attribution_channel": self.attribution_channel,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class CustomerEvent(Base):
    __tablename__ = 'customer_events'
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    event_type = Column(String(50), nullable=False) # 'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICK', 'CONVERSION', 'APP_STAGE_LOGIN', etc.
    event_source = Column(String(20), nullable=False) # 'Moengage', 'LOS'
    event_timestamp = Column(DateTime(timezone=True), default=datetime.now)
    event_details = Column(JSONB) # Stores specific event data (e.g., application stage details)

    def to_dict(self):
        return {
            "event_id": str(self.event_id),
            "customer_id": str(self.customer_id),
            "event_type": self.event_type,
            "event_source": self.event_source,
            "event_timestamp": self.event_timestamp.isoformat() if self.event_timestamp else None,
            "event_details": self.event_details,
        }

class Campaign(Base):
    __tablename__ = 'campaigns'
    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_unique_identifier = Column(String(100), unique=True, nullable=False)
    campaign_name = Column(String(255), nullable=False)
    campaign_date = Column(Date)
    targeted_customers_count = Column(Integer)
    attempted_count = Column(Integer)
    successfully_sent_count = Column(Integer)
    failed_count = Column(Integer)
    success_rate = Column(Numeric(5,2))
    conversion_rate = Column(Numeric(5,2))
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "campaign_id": str(self.campaign_id),
            "campaign_unique_identifier": self.campaign_unique_identifier,
            "campaign_name": self.campaign_name,
            "campaign_date": self.campaign_date.isoformat() if self.campaign_date else None,
            "targeted_customers_count": self.targeted_customers_count,
            "attempted_count": self.attempted_count,
            "successfully_sent_count": self.successfully_sent_count,
            "failed_count": self.failed_count,
            "success_rate": float(self.success_rate) if self.success_rate else None,
            "conversion_rate": float(self.conversion_rate) if self.conversion_rate else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class DataIngestionLog(Base):
    __tablename__ = 'data_ingestion_logs'
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), default=datetime.now)
    status = Column(String(20), nullable=False) # 'SUCCESS', 'FAILED', 'PARTIAL'
    error_details = Column(String) # TEXT in schema, String is fine for variable length text
    uploaded_by = Column(String(100))

    def to_dict(self):
        return {
            "log_id": str(self.log_id),
            "file_name": self.file_name,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "status": self.status,
            "error_details": self.error_details,
            "uploaded_by": self.uploaded_by,
        }

# --- Flask Blueprint ---
customer_bp = Blueprint('customer_routes', __name__, url_prefix='/api')

# --- Helper Functions (Mocked for now, real logic would be more complex) ---
def process_lead_data(data):
    """
    Mocks lead processing, including deduplication and customer creation/update.
    FR2, FR3, FR4, FR5, FR10
    """
    session = Session()
    try:
        mobile_number = data.get('mobile_number')
        pan = data.get('pan')
        aadhaar_ref_number = data.get('aadhaar_ref_number')
        ucid = data.get('ucid')
        previous_loan_app_number = data.get('previous_loan_app_number')

        if not mobile_number:
            return {"status": "error", "message": "Mobile number is required for lead processing."}

        # Basic deduplication logic (FR2, FR3, FR4, FR5)
        # Prioritize matching based on provided identifiers
        customer = session.query(Customer).filter(
            (Customer.mobile_number == mobile_number) |
            (Customer.pan == pan if pan else False) |
            (Customer.aadhaar_ref_number == aadhaar_ref_number if aadhaar_ref_number else False) |
            (Customer.ucid == ucid if ucid else False) |
            (Customer.previous_loan_app_number == previous_loan_app_number if previous_loan_app_number else False)
        ).first()

        if not customer:
            customer = Customer(
                mobile_number=mobile_number,
                pan=pan,
                aadhaar_ref_number=aadhaar_ref_number,
                ucid=ucid,
                previous_loan_app_number=previous_loan_app_number,
                customer_attributes=data.get('customer_attributes', {}),
                customer_segment=data.get('customer_segment')
            )
            session.add(customer)
            session.flush() # To get customer_id before commit
            message = "New lead created."
        else:
            # Update existing customer attributes if necessary (FR14)
            customer.customer_attributes = {**customer.customer_attributes, **data.get('customer_attributes', {})}
            customer.customer_segment = data.get('customer_segment') or customer.customer_segment
            customer.updated_at = datetime.now() # Explicitly update timestamp
            message = "Existing customer updated with new lead data."

        # Store event data (FR21, FR22)
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type="LEAD_GENERATED",
            event_source=data.get('source_channel', 'API'),
            event_details=data
        )
        session.add(event)

        session.commit()
        return {"status": "success", "message": message, "customer_id": str(customer.customer_id)}
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error during lead processing: {e}")
        return {"status": "error", "message": "Database error during lead processing."}
    except Exception as e:
        session.rollback()
        print(f"Error during lead processing: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    finally:
        session.close()

def process_eligibility_data(data):
    """
    Mocks eligibility data processing.
    FR9, FR10
    """
    session = Session()
    try:
        loan_app_number = data.get('loan_application_number')
        mobile_number = data.get('mobile_number')
        eligibility_status = data.get('eligibility_status')
        offer_id = data.get('offer_id')
        source_channel = data.get('source_channel', 'API')

        customer = session.query(Customer).filter_by(mobile_number=mobile_number).first()
        if not customer:
            return {"status": "error", "message": "Customer not found for eligibility update."}

        offer = None
        if offer_id:
            offer = session.query(Offer).filter_by(offer_id=offer_id).first()
        elif loan_app_number:
            offer = session.query(Offer).filter_by(loan_application_number=loan_app_number).first()

        if offer:
            # FR13: Prevent modification if loan application journey started and not expired/rejected
            if offer.loan_application_number and offer.offer_status not in ['Expired', 'Rejected']:
                return {"status": "error", "message": "Offer cannot be modified as loan application journey has started."}
            
            offer.offer_status = eligibility_status # Example: 'Eligible', 'Not Eligible' (FR15)
            offer.updated_at = datetime.now()
        else:
            # Create a new offer entry if it's a new eligibility check for a new offer
            offer = Offer(
                customer_id=customer.customer_id,
                offer_type="Eligibility Check", # Or derive from context (FR16)
                offer_status=eligibility_status,
                loan_application_number=loan_app_number,
                attribution_channel=source_channel
            )
            session.add(offer)

        # Store event data (FR21, FR22)
        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type="ELIGIBILITY_CHECK",
            event_source=source_channel,
            event_details=data
        )
        session.add(event)

        session.commit()
        return {"status": "success", "message": "Eligibility data processed."}
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error during eligibility processing: {e}")
        return {"status": "error", "message": "Database error during eligibility processing."}
    except Exception as e:
        session.rollback()
        print(f"Error during eligibility processing: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    finally:
        session.close()

def process_status_update_data(data):
    """
    Mocks loan application status update processing.
    FR9, FR10, FR21, FR22
    """
    session = Session()
    try:
        loan_app_number = data.get('loan_application_number')
        application_stage = data.get('application_stage')
        status_details = data.get('status_details')
        event_timestamp_str = data.get('event_timestamp')

        if not loan_app_number or not application_stage:
            return {"status": "error", "message": "Loan application number and application stage are required."}

        offer = session.query(Offer).filter_by(loan_application_number=loan_app_number).first()
        if not offer:
            return {"status": "error", "message": "Offer not found for status update."}

        customer_id = offer.customer_id
        
        event_timestamp = datetime.fromisoformat(event_timestamp_str) if event_timestamp_str else datetime.now()

        # Store event data (FR21, FR22)
        event = CustomerEvent(
            customer_id=customer_id,
            event_type=f"APP_STAGE_{application_stage.upper()}",
            event_source="LOS", # Assuming LOS for application stages
            event_timestamp=event_timestamp,
            event_details={"stage": application_stage, "details": status_details}
        )
        session.add(event)

        # Update offer status if it's a final status (e.g., 'Rejected', 'Expired') (FR13, FR38)
        if application_stage.lower() in ['expired', 'rejected']:
            offer.offer_status = application_stage.capitalize()
            offer.updated_at = datetime.now()

        session.commit()
        return {"status": "success", "message": "Status updated."}
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error during status update: {e}")
        return {"status": "error", "message": "Database error during status update."}
    except Exception as e:
        session.rollback()
        print(f"Error during status update: {e}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    finally:
        session.close()

def process_customer_details_upload(file_type, file_content_base64, uploaded_by):
    """
    Mocks processing of uploaded customer details file.
    FR29, FR30, FR31, FR32
    """
    log_id = uuid.uuid4()
    session = Session()
    try:
        decoded_content = base64.b64decode(file_content_base64).decode('utf-8')
        # In a real scenario, parse CSV/Excel here (e.g., using pandas)
        # For now, simulate processing and generate success/error
        lines = decoded_content.strip().split('\n')
        if not lines:
            raise ValueError("Uploaded file is empty.")
        
        header = lines[0].strip().split(',')
        data_rows = lines[1:]

        total_records = len(data_rows)
        processed_success = 0
        processed_failed = 0
        error_records = []

        # Simulate processing each row
        for i, line in enumerate(data_rows):
            if not line.strip(): continue # Skip empty lines

            parts = line.split(',') # Simple CSV assumption
            # Basic validation (FR1) - check if enough columns and mobile/PAN are present
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                mobile = parts[0].strip()
                pan = parts[1].strip()
                
                # Simulate lead generation (FR30)
                lead_data = {
                    "mobile_number": mobile,
                    "pan": pan,
                    "loan_type": file_type,
                    "source_channel": "Admin_Upload",
                    "customer_attributes": {"upload_type": file_type, "original_row": line}
                }
                result = process_lead_data(lead_data) # Re-use lead processing logic
                if result.get("status") == "success":
                    processed_success += 1
                else:
                    processed_failed += 1
                    error_records.append(f"Row {i+2}: {line} - {result.get('message', 'Unknown error')}") # +2 for header and 0-index
            else:
                processed_failed += 1
                error_records.append(f"Row {i+2}: {line} - Invalid format or missing required fields (mobile, PAN).")

        status = "SUCCESS" if processed_failed == 0 else ("PARTIAL" if processed_success > 0 else "FAILED")
        error_details = "\n".join(error_records) if error_records else None

        log_entry = DataIngestionLog(
            log_id=log_id,
            file_name=f"{file_type}_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            upload_timestamp=datetime.now(),
            status=status,
            error_details=error_details,
            uploaded_by=uploaded_by
        )
        session.add(log_entry)
        session.commit()

        message = f"File uploaded and processing initiated. Total: {total_records}, Success: {processed_success}, Failed: {processed_failed}."
        if status == "PARTIAL":
            message += " Some records failed. Download error file for details."
        elif status == "FAILED":
            message = "File upload failed completely. Download error file for details."
        else:
            message = "File uploaded successfully. All records processed."

        return {"status": status, "message": message, "log_id": str(log_id)}

    except Exception as e:
        session.rollback()
        log_entry = DataIngestionLog(
            log_id=log_id,
            file_name=f"{file_type}_upload_error_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            upload_timestamp=datetime.now(),
            status="FAILED",
            error_details=f"File processing error: {str(e)}",
            uploaded_by=uploaded_by
        )
        session.add(log_entry)
        session.commit()
        print(f"Error processing customer details upload: {e}")
        return {"status": "error", "message": f"Failed to process file: {str(e)}", "log_id": str(log_id)}
    finally:
        session.close()

def generate_moengage_file():
    """
    Mocks generation of Moengage CSV file.
    FR25, FR39
    """
    session = Session()
    try:
        # Fetch customers who are not DND and have active offers (FR21)
        # This is a simplified query; real logic would involve campaign data, offer types etc.
        # Ensure distinct customers even if they have multiple active offers
        customers_for_moengage = session.query(Customer).join(Offer).filter(
            Customer.is_dnd == False,
            Offer.offer_status == 'Active'
        ).distinct(Customer.customer_id).all()

        output = io.StringIO()
        # Moengage file format usually requires specific headers
        output.write("mobile_number,customer_id,offer_id,offer_type,campaign_name,customer_segment\n") # Example headers
        for customer in customers_for_moengage:
            # Get one active offer for the customer (simplified for this mock)
            offer = session.query(Offer).filter_by(customer_id=customer.customer_id, offer_status='Active').first()
            if offer:
                # Mock campaign name for now, in reality it would come from campaign data
                campaign_name = "Default_Moengage_Campaign"
                output.write(f"{customer.mobile_number},{customer.customer_id},{offer.offer_id},{offer.offer_type},{campaign_name},{customer.customer_segment or ''}\n")

        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"Error generating Moengage file: {e}")
        return None
    finally:
        session.close()

def generate_duplicate_data_file():
    """
    Mocks generation of Duplicate Data File.
    FR26
    """
    session = Session()
    try:
        # This is a highly simplified mock. Real deduplication results would come from a dedicated process
        # or a specific table storing duplicate groups.
        # For demonstration, we'll find customers that share a PAN but have different mobile numbers (mock scenario)
        # In a real system, this would query a pre-computed deduplication result set.
        
        # Example: Find PANs that appear more than once with different mobile numbers
        subquery = session.query(Customer.pan).group_by(Customer.pan).having(
            func.count(distinct(Customer.mobile_number)) > 1
        ).subquery()

        duplicate_pan_customers = session.query(Customer).join(
            subquery, Customer.pan == subquery.c.pan
        ).order_by(Customer.pan, Customer.mobile_number).all()

        output = io.StringIO()
        output.write("customer_id,mobile_number,pan,aadhaar_ref_number,duplicate_reason\n")
        
        # Group by PAN to show duplicates
        current_pan = None
        for customer in duplicate_pan_customers:
            if customer.pan != current_pan:
                output.write(f"\n--- Duplicates for PAN: {customer.pan} ---\n")
                current_pan = customer.pan
            output.write(f"{customer.customer_id},{customer.mobile_number},{customer.pan or ''},{customer.aadhaar_ref_number or ''},PAN_Match\n")

        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"Error generating duplicate data file: {e}")
        return None
    finally:
        session.close()

from sqlalchemy import func, distinct # Added for generate_duplicate_data_file

def generate_unique_data_file():
    """
    Mocks generation of Unique Data File.
    FR27
    """
    session = Session()
    try:
        # Fetch all unique customers (after deduplication logic has run)
        # In a real system, this would be the result of the deduplication process,
        # where only the "master" customer profiles are considered unique.
        unique_customers = session.query(Customer).all() # Assuming the 'customers' table already holds unique profiles post-dedupe

        output = io.StringIO()
        output.write("customer_id,mobile_number,pan,aadhaar_ref_number,ucid,customer_segment,is_dnd\n")
        for customer in unique_customers:
            output.write(f"{customer.customer_id},{customer.mobile_number},{customer.pan or ''},{customer.aadhaar_ref_number or ''},{customer.ucid or ''},{customer.customer_segment or ''},{customer.is_dnd}\n")

        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"Error generating unique data file: {e}")
        return None
    finally:
        session.close()

def generate_error_excel_file(log_id=None):
    """
    Mocks generation of Error Excel file.
    FR28, FR32
    """
    session = Session()
    try:
        log_entry = None
        if log_id:
            log_entry = session.query(DataIngestionLog).filter_by(log_id=log_id).first()
        else:
            # Fetch the most recent failed/partial log if no specific log_id is provided
            log_entry = session.query(DataIngestionLog).filter(
                DataIngestionLog.status.in_(['FAILED', 'PARTIAL'])
            ).order_by(DataIngestionLog.upload_timestamp.desc()).first()
            
        if not log_entry or not log_entry.error_details:
            return None # No errors or log not found

        error_data = log_entry.error_details.split('\n')

        # In a real scenario, use pandas to create an Excel file (.xlsx)
        # For now, return a CSV-like string that can be opened by Excel.
        output = io.StringIO()
        output.write("Error Description,Original Data\n")
        for line in error_data:
            if " - " in line:
                parts = line.split(" - ", 1)
                original_data = parts[0].strip()
                error_desc = parts[1].strip()
                output.write(f'"{error_desc}","{original_data}"\n')
            else:
                output.write(f'"{line}",""\n') # Fallback for lines without " - "

        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"Error generating error Excel file: {e}")
        return None
    finally:
        session.close()

# --- API Endpoints ---

@customer_bp.route('/leads', methods=['POST'])
def create_lead():
    data = request.get_json()
    if not data or not data.get('mobile_number'):
        abort(400, description="Mobile number is required for lead generation.")
    
    result = process_lead_data(data)
    if result.get("status") == "error":
        return jsonify({"message": result["message"]}), 500
    return jsonify(result), 200

@customer_bp.route('/eligibility', methods=['POST'])
def update_eligibility():
    data = request.get_json()
    if not data or not data.get('mobile_number') or not data.get('eligibility_status'):
        abort(400, description="Mobile number and eligibility status are required.")
    
    result = process_eligibility_data(data)
    if result.get("status") == "error":
        return jsonify({"message": result["message"]}), 500
    return jsonify(result), 200

@customer_bp.route('/status', methods=['POST'])
def update_status():
    data = request.get_json()
    if not data or not data.get('loan_application_number') or not data.get('application_stage'):
        abort(400, description="Loan application number and application stage are required.")
    
    result = process_status_update_data(data)
    if result.get("status") == "error":
        return jsonify({"message": result["message"]}), 500
    return jsonify(result), 200

@customer_bp.route('/admin/upload/customer-details', methods=['POST'])
def upload_customer_details():
    data = request.get_json()
    if not data or not data.get('file_type') or not data.get('file_content_base64') or not data.get('uploaded_by'):
        abort(400, description="File type, file content (base64), and uploader are required.")
    
    result = process_customer_details_upload(
        data['file_type'],
        data['file_content_base64'],
        data['uploaded_by']
    )
    if result.get("status") == "error":
        return jsonify({"message": result["message"], "log_id": result.get("log_id")}), 500
    return jsonify(result), 200

@customer_bp.route('/reports/moengage-file', methods=['GET'])
def download_moengage_file():
    file_content = generate_moengage_file()
    if file_content is None:
        abort(500, description="Failed to generate Moengage file.")
    
    return send_file(
        io.BytesIO(file_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'moengage_campaign_data_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
    )

@customer_bp.route('/reports/duplicate-data', methods=['GET'])
def download_duplicate_data():
    file_content = generate_duplicate_data_file()
    if file_content is None:
        abort(500, description="Failed to generate duplicate data file.")
    
    return send_file(
        io.BytesIO(file_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'duplicate_customer_data_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
    )

@customer_bp.route('/reports/unique-data', methods=['GET'])
def download_unique_data():
    file_content = generate_unique_data_file()
    if file_content is None:
        abort(500, description="Failed to generate unique data file.")
    
    return send_file(
        io.BytesIO(file_content.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'unique_customer_data_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
    )

@customer_bp.route('/reports/error-data', methods=['GET'])
def download_error_data():
    log_id = request.args.get('log_id') # Allow fetching specific error log
    file_content = generate_error_excel_file(log_id)
    if file_content is None:
        abort(404, description="No error data found for the given log ID or no recent errors.")
    
    # For a real Excel file, you'd use a library like openpyxl or pandas.to_excel.
    # For now, sending as CSV content with an .xlsx extension and appropriate mimetype.
    return send_file(
        io.BytesIO(file_content.encode('utf-8')),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # Mime type for .xlsx
        as_attachment=True,
        download_name=f'error_data_{log_id or datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    )

@customer_bp.route('/reports/daily-tally', methods=['GET'])
def get_daily_tally_report():
    # Mock data for daily tally report (FR35)
    # In a real scenario, this would query aggregated data from the DB
    report_date_str = request.args.get('date', date.today().isoformat())
    try:
        report_date = date.fromisoformat(report_date_str)
    except ValueError:
        abort(400, description="Invalid date format. Use YYYY-MM-DD.")
    
    session = Session()
    try:
        # Example: Count customers created today
        start_of_day = datetime.combine(report_date, datetime.min.time())
        end_of_day = datetime.combine(report_date, datetime.max.time())

        total_customers_processed = session.query(Customer).filter(
            Customer.created_at >= start_of_day,
            Customer.created_at <= end_of_day
        ).count()

        # Example: Count new offers generated today
        new_offers_generated = session.query(Offer).filter(
            Offer.created_at >= start_of_day,
            Offer.created_at <= end_of_day
        ).count()

        # Deduplicated customers would require more complex logic/tables. Mocking for now.
        deduplicated_customers = int(total_customers_processed * 0.1) # Mock 10% deduplication

        return jsonify({
            "date": report_date_str,
            "total_customers_processed": total_customers_processed,
            "new_offers_generated": new_offers_generated,
            "deduplicated_customers": deduplicated_customers
        }), 200
    except Exception as e:
        print(f"Error fetching daily tally report: {e}")
        abort(500, description="Failed to retrieve daily tally report.")
    finally:
        session.close()

@customer_bp.route('/customer/<uuid:customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    session = Session()
    try:
        customer = session.query(Customer).filter_by(customer_id=customer_id).first()
        if not customer:
            abort(404, description="Customer not found.")
        
        # Fetch active offers (FR15)
        offers = session.query(Offer).filter_by(customer_id=customer_id, offer_status='Active').all()
        
        # Fetch recent customer events/application stages (FR22, FR36)
        events = session.query(CustomerEvent).filter_by(customer_id=customer_id).order_by(CustomerEvent.event_timestamp.desc()).limit(10).all() # Limit for brevity

        customer_data = customer.to_dict()
        customer_data['active_offers'] = [offer.to_dict() for offer in offers]
        customer_data['application_stages'] = [event.to_dict() for event in events] # Renamed from 'events' to 'application_stages' as per API spec

        return jsonify(customer_data), 200
    except SQLAlchemyError as e:
        print(f"Database error fetching customer profile: {e}")
        abort(500, description="Database error retrieving customer profile.")
    except Exception as e:
        print(f"Error fetching customer profile: {e}")
        abort(500, description=f"An unexpected error occurred: {str(e)}")
    finally:
        session.close()