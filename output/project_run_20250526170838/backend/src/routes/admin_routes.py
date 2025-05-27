from flask import Blueprint, request, jsonify, current_app
import base64
import csv
import io
import uuid
from datetime import datetime, date

# Attempt to import db and models from the main src package.
# This assumes `src` is a Python package and `db` (SQLAlchemy instance)
# and model classes (Customer, Offer, IngestionLog) are defined within it.
# This is the standard way to fix the "attempted relative import with no known parent package"
# error when running a sub-module directly or if the package structure isn't correctly set up.
try:
    from src import db
    from src.models import Customer, Offer, IngestionLog
except ImportError:
    # Fallback for isolated testing or if the project structure differs,
    # providing mock objects to allow the code to be syntactically valid
    # and runnable without the full Flask app context or actual models.
    # In a real deployment, these mocks would be removed, and the
    # `from src import db` import would correctly resolve.
    print("WARNING: Could not import 'db' or models from 'src'. Using mock objects.")
    print("Ensure 'src' is a recognized Python package and 'db' and models are defined.")

    class MockDB:
        def __init__(self):
            self.session = MockSession()
        def init_app(self, app): pass
        def create_all(self): pass
        def drop_all(self): pass

    class MockSession:
        def add(self, obj): pass
        def commit(self): pass
        def rollback(self): pass
        def query(self, model): return MockQuery(model)

    class MockQuery:
        def __init__(self, model): self.model = model
        def filter_by(self, **kwargs): return self
        def first(self): return None
        def all(self): return []

    db = MockDB()

    # Mock SQLAlchemy models for compilation purposes
    class Customer:
        def __init__(self, customer_id, mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None, loan_application_number=None, dnd_flag=False, segment=None):
            self.customer_id = customer_id
            self.mobile_number = mobile_number
            self.pan_number = pan_number
            self.aadhaar_number = aadhaar_number
            self.ucid_number = ucid_number
            self.loan_application_number = loan_application_number
            self.dnd_flag = dnd_flag
            self.segment = segment
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
        def __repr__(self): return f"<Customer {self.customer_id}>"

    class Offer:
        def __init__(self, offer_id, customer_id, offer_type=None, offer_status=None, propensity=None, start_date=None, end_date=None, channel=None):
            self.offer_id = offer_id
            self.customer_id = customer_id
            self.offer_type = offer_type
            self.offer_status = offer_status
            self.propensity = propensity
            self.start_date = start_date
            self.end_date = end_date
            self.channel = channel
            self.created_at = datetime.now()
            self.updated_at = datetime.now()

    class IngestionLog:
        def __init__(self, log_id, file_name, upload_timestamp, status, error_description=None):
            self.log_id = log_id
            self.file_name = file_name
            self.upload_timestamp = upload_timestamp
            self.status = status
            self.error_description = error_description
        def __repr__(self): return f"<IngestionLog {self.log_id}>"


# Create a Blueprint for admin routes
bp = Blueprint('admin_routes', __name__)

@bp.route('/customer-data/upload', methods=['POST'])
def upload_customer_data():
    """
    Handles the upload of customer details file (Prospect, TW Loyalty, Topup, Employee loans)
    via Admin Portal.
    - Decodes base64 CSV content.
    - Parses CSV rows.
    - Performs basic column-level validation.
    - Implements simplified deduplication (upsert based on identifiers).
    - Creates/updates customer and offer records.
    - Logs ingestion status and errors.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400

    file_content_b64 = data.get('file_content')
    file_name = data.get('file_name')
    loan_type = data.get('loan_type') # e.g., 'Prospect', 'TW Loyalty', 'Topup', 'Employee'

    if not all([file_content_b64, file_name, loan_type]):
        return jsonify({"status": "error", "message": "Missing file_content, file_name, or loan_type"}), 400

    log_id = str(uuid.uuid4())
    initial_log_status = "FAILED"
    initial_error_description = None

    try:
        decoded_content = base64.b64decode(file_content_b64).decode('utf-8')
        csv_file = io.StringIO(decoded_content)
        csv_reader = csv.DictReader(csv_file)

        # Define expected columns for basic validation (FR1)
        # These are examples; actual columns would come from detailed BRD specs.
        expected_columns = [
            'mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number',
            'loan_application_number', 'dnd_flag', 'segment', 'offer_type',
            'offer_status', 'propensity', 'start_date', 'end_date', 'channel'
        ]

        # Check if all expected columns are present in the CSV header
        missing_cols = [col for col in expected_columns if col not in csv_reader.fieldnames]
        if missing_cols:
            initial_error_description = f"Missing required columns in CSV: {', '.join(missing_cols)}"
            raise ValueError(initial_error_description)

        success_count = 0
        error_count = 0
        errors_list = [] # To store row-level errors for potential error file generation

        for row_num, row in enumerate(csv_reader, start=2): # Start from 2 for header + first data row
            try:
                # Basic row-level validation: At least one identifier must be present
                if not any(row.get(col) for col in ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number', 'loan_application_number']):
                    raise ValueError("At least one customer identifier (mobile, PAN, Aadhaar, UCID, LAN) is required for each row.")

                # Deduplication logic (FR3, FR4, FR5, FR6 - simplified upsert)
                # Check if customer exists based on any provided identifier
                existing_customer = None
                if row.get('mobile_number'):
                    existing_customer = db.session.query(Customer).filter_by(mobile_number=row['mobile_number']).first()
                if not existing_customer and row.get('pan_number'):
                    existing_customer = db.session.query(Customer).filter_by(pan_number=row['pan_number']).first()
                if not existing_customer and row.get('aadhaar_number'):
                    existing_customer = db.session.query(Customer).filter_by(aadhaar_number=row['aadhaar_number']).first()
                if not existing_customer and row.get('ucid_number'):
                    existing_customer = db.session.query(Customer).filter_by(ucid_number=row['ucid_number']).first()
                if not existing_customer and row.get('loan_application_number'):
                    existing_customer = db.session.query(Customer).filter_by(loan_application_number=row['loan_application_number']).first()

                customer_id = None
                if existing_customer:
                    # Update existing customer details (FR8 - update old offers, implies customer update)
                    customer_id = existing_customer.customer_id
                    existing_customer.mobile_number = row.get('mobile_number') or existing_customer.mobile_number
                    existing_customer.pan_number = row.get('pan_number') or existing_customer.pan_number
                    existing_customer.aadhaar_number = row.get('aadhaar_number') or existing_customer.aadhaar_number
                    existing_customer.ucid_number = row.get('ucid_number') or existing_customer.ucid_number
                    existing_customer.loan_application_number = row.get('loan_application_number') or existing_customer.loan_application_number
                    existing_customer.dnd_flag = row.get('dnd_flag', 'FALSE').upper() == 'TRUE' # FR23: DND flag
                    existing_customer.segment = row.get('segment') or existing_customer.segment # FR15, FR20: Segments
                    existing_customer.updated_at = datetime.now()
                    db.session.add(existing_customer)
                else:
                    # Create new customer (FR36 - generate leads)
                    customer_id = str(uuid.uuid4())
                    new_customer = Customer(
                        customer_id=customer_id,
                        mobile_number=row.get('mobile_number'),
                        pan_number=row.get('pan_number'),
                        aadhaar_number=row.get('aadhaar_number'),
                        ucid_number=row.get('ucid_number'),
                        loan_application_number=row.get('loan_application_number'),
                        dnd_flag=row.get('dnd_flag', 'FALSE').upper() == 'TRUE',
                        segment=row.get('segment'),
                    )
                    db.session.add(new_customer)

                # Process offer data associated with the customer
                # FR16: Maintain flags for Offer statuses (Active, Inactive, Expired)
                # FR17: Maintain flags for Offer types ('Fresh', 'Enrich', 'New-old', 'New-new')
                # FR18: Maintain analytics-defined flags for Propensity
                offer_id = str(uuid.uuid4())
                start_date_obj = datetime.strptime(row['start_date'], '%Y-%m-%d').date() if row.get('start_date') else None
                end_date_obj = datetime.strptime(row['end_date'], '%Y-%m-%d').date() if row.get('end_date') else None

                new_offer = Offer(
                    offer_id=offer_id,
                    customer_id=customer_id,
                    offer_type=row.get('offer_type'),
                    offer_status=row.get('offer_status', 'Active'), # Default to Active if not provided
                    propensity=row.get('propensity'),
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    channel=row.get('channel')
                )
                db.session.add(new_offer)

                db.session.commit() # Commit each row for atomicity or consider batch commit for performance
                success_count += 1

            except Exception as e:
                db.session.rollback() # Rollback changes for the current row if an error occurs
                error_count += 1
                errors_list.append({
                    "row_number": row_num,
                    "data": row,
                    "error_desc": str(e)
                })
                # Log row-specific errors for debugging
                current_app.logger.error(f"Error processing row {row_num} in {file_name}: {e}")

        # Log the overall ingestion status (FR37, FR38)
        status = "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS" if success_count > 0 else "FAILED"
        overall_error_description = None
        if errors_list:
            # For simplicity, store a summary of errors in the log.
            # A more robust solution would store detailed errors in a separate table
            # or generate a specific error file (handled by /data/errors endpoint).
            overall_error_description = f"{error_count} errors encountered. First error: {errors_list[0]['error_desc']}"

        ingestion_log = IngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status=status,
            error_description=overall_error_description
        )
        db.session.add(ingestion_log)
        db.session.commit()

        return jsonify({
            "status": status,
            "log_id": log_id,
            "success_count": success_count,
            "error_count": error_count,
            "message": "File processed successfully." if status == "SUCCESS" else "File processed with errors."
        }), 200

    except Exception as e:
        db.session.rollback() # Rollback any pending transactions from parsing/initial validation errors
        final_error_msg = initial_error_description if initial_error_description else f"Failed to process file {file_name}: {e}"
        current_app.logger.error(final_error_msg)

        # Log the initial failure if it occurred before row processing
        ingestion_log = IngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status="FAILED",
            error_description=final_error_msg
        )
        db.session.add(ingestion_log)
        db.session.commit()

        return jsonify({
            "status": "error",
            "message": final_error_msg,
            "log_id": log_id,
            "success_count": 0,
            "error_count": 0
        }), 500