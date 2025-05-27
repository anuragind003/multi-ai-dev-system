import io
import csv
import base64
import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file
from sqlalchemy.exc import SQLAlchemyError

# --- Mock Database Models and Services (for demonstration purposes) ---
# In a real application, these would be imported from `backend.models`
# and `backend.services` respectively.
# For this exercise, we define simple mock classes to make the code runnable
# and demonstrate the intended interactions.

class MockCustomer:
    """Mock Customer Model."""
    def __init__(self, customer_id, mobile_number=None, pan_number=None,
                 aadhaar_number=None, ucid_number=None,
                 loan_application_number=None, dnd_flag=False, segment=None):
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

    def to_dict(self):
        """Convert customer object to dictionary."""
        return {
            "customer_id": self.customer_id,
            "mobile_number": self.mobile_number,
            "pan_number": self.pan_number,
            "aadhaar_number": self.aadhaar_number,
            "ucid_number": self.ucid_number,
            "loan_application_number": self.loan_application_number,
            "dnd_flag": self.dnd_flag,
            "segment": self.segment,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class MockOffer:
    """Mock Offer Model."""
    def __init__(self, offer_id, customer_id, offer_type, offer_status,
                 propensity, start_date, end_date, channel):
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

    def to_dict(self):
        """Convert offer object to dictionary."""
        return {
            "offer_id": self.offer_id,
            "customer_id": self.customer_id,
            "offer_type": self.offer_type,
            "offer_status": self.offer_status,
            "propensity": self.propensity,
            "start_date": (self.start_date.isoformat()
                           if self.start_date else None),
            "end_date": (self.end_date.isoformat()
                         if self.end_date else None),
            "channel": self.channel,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class MockIngestionLog:
    """Mock IngestionLog Model."""
    def __init__(self, log_id, file_name, status, error_description=None):
        self.log_id = log_id
        self.file_name = file_name
        self.upload_timestamp = datetime.now()
        self.status = status
        self.error_description = error_description

    def to_dict(self):
        """Convert ingestion log object to dictionary."""
        return {
            "log_id": self.log_id,
            "file_name": self.file_name,
            "upload_timestamp": self.upload_timestamp.isoformat(),
            "status": self.status,
            "error_description": self.error_description
        }


class MockDB:
    """A simple mock database to simulate SQLAlchemy interactions."""
    def __init__(self):
        self.customers = {}
        self.offers = {}
        self.ingestion_logs = {}

    def add(self, obj):
        """Add an object to the mock database."""
        if isinstance(obj, MockCustomer):
            self.customers[obj.customer_id] = obj
        elif isinstance(obj, MockOffer):
            self.offers[obj.offer_id] = obj
        elif isinstance(obj, MockIngestionLog):
            self.ingestion_logs[obj.log_id] = obj

    def commit(self):
        """Simulate a database commit."""
        pass

    def rollback(self):
        """Simulate a database rollback."""
        pass

    def query(self, model):
        """Simulate querying the database."""
        if model == MockCustomer:
            return list(self.customers.values())
        if model == MockIngestionLog:
            return list(self.ingestion_logs.values())
        return []

    def get_customer_by_identifiers(self, customer_id=None, mobile=None,
                                    pan=None, aadhaar=None, ucid=None,
                                    lan=None):
        """Simulate fetching a customer by various identifiers."""
        if customer_id and customer_id in self.customers:
            return self.customers[customer_id]

        for customer in self.customers.values():
            if (mobile and customer.mobile_number == mobile) or \
               (pan and customer.pan_number == pan) or \
               (aadhaar and customer.aadhaar_number == aadhaar) or \
               (ucid and customer.ucid_number == ucid) or \
               (lan and customer.loan_application_number == lan):
                return customer
        return None

# Initialize mock DB
db = MockDB()


class MockDeduplicationService:
    """
    A mock service to simulate deduplication and customer data processing.
    In a real system, this would be a complex service handling FR3, FR4, FR5,
    FR6, FR17, FR36.
    """
    def process_customer_data(self, customer_data):
        """
        Simulates processing customer data, including deduplication.
        Returns (customer_id, status, error_message)
        """
        customer_id = str(uuid.uuid4())
        mobile = customer_data.get('mobile_number')
        pan = customer_data.get('pan_number')
        aadhaar = customer_data.get('aadhaar_number')
        ucid = customer_data.get('ucid_number')
        lan = customer_data.get('loan_application_number')

        # Simulate deduplication check
        existing_customer = db.get_customer_by_identifiers(
            mobile=mobile, pan=pan, aadhaar=aadhaar, ucid=ucid, lan=lan
        )

        if existing_customer:
            # Simulate update of existing customer
            existing_customer.mobile_number = mobile or \
                existing_customer.mobile_number
            existing_customer.pan_number = pan or existing_customer.pan_number
            existing_customer.aadhaar_number = aadhaar or \
                existing_customer.aadhaar_number
            existing_customer.ucid_number = ucid or existing_customer.ucid_number
            existing_customer.loan_application_number = lan or \
                existing_customer.loan_application_number
            existing_customer.dnd_flag = customer_data.get(
                'dnd_flag', existing_customer.dnd_flag
            )
            existing_customer.segment = customer_data.get(
                'segment', existing_customer.segment
            )
            existing_customer.updated_at = datetime.now()
            db.add(existing_customer)  # "update" in mock db
            return existing_customer.customer_id, "updated", None
        else:
            # Simulate new customer creation
            new_customer = MockCustomer(
                customer_id=customer_id,
                mobile_number=mobile,
                pan_number=pan,
                aadhaar_number=aadhaar,
                ucid_number=ucid,
                loan_application_number=lan,
                dnd_flag=customer_data.get('dnd_flag', False),
                segment=customer_data.get('segment')
            )
            db.add(new_customer)
            return customer_id, "created", None

    def get_duplicate_records(self):
        """Simulates fetching duplicate records."""
        # In a real system, this would query a dedicated table
        # or run a complex deduplication report.
        # For mock, return some sample data.
        return [
            {"mobile_number": "9876543210", "pan_number": "ABCDE1234F",
             "reason": "Duplicate Mobile/PAN"},
            {"mobile_number": "9998887770", "aadhaar_number": "123456789012",
             "reason": "Duplicate Aadhaar"}
        ]

    def get_unique_records(self):
        """Simulates fetching unique records."""
        # For mock, return all current customers
        return [c.to_dict() for c in db.query(MockCustomer)]

deduplication_service = MockDeduplicationService()

# --- End Mock Database Models and Services ---


admin_portal_bp = Blueprint('admin_portal_bp', __name__)


@admin_portal_bp.route('/admin/customer-data/upload', methods=['POST'])
def upload_customer_data():
    """
    Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans)
    via Admin Portal.
    Generates leads, success/error files. (FR35, FR36, FR37, FR38)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    file_content_b64 = data.get('file_content')
    file_name = data.get('file_name')
    loan_type = data.get('loan_type')

    if not all([file_content_b64, file_name, loan_type]):
        return jsonify({
            "error": "Missing file_content, file_name, or loan_type"
        }), 400

    log_id = str(uuid.uuid4())
    ingestion_log = MockIngestionLog(
        log_id=log_id,
        file_name=file_name,
        status="PROCESSING"
    )
    db.add(ingestion_log)
    db.commit()  # Commit the log entry immediately

    try:
        decoded_content = base64.b64decode(file_content_b64).decode('utf-8')
        csv_file = io.StringIO(decoded_content)
        reader = csv.DictReader(csv_file)

        success_count = 0
        error_count = 0
        errors = []

        for i, row in enumerate(reader):
            # Basic column-level validation (FR1, NFR3)
            # This is a simplified example. Real validation would be more robust
            # and potentially use a dedicated validation service.
            required_fields = ['mobile_number', 'pan_number']
            if not all(row.get(field) for field in required_fields):
                error_count += 1
                errors.append(
                    f"Row {i+1}: Missing required fields. Data: {row}"
                )
                continue

            try:
                # Call deduplication and ingestion service
                # This service would handle FR3, FR4, FR5, FR6, FR17, FR36
                customer_id, status, error_msg = \
                    deduplication_service.process_customer_data(row)
                if status in ["created", "updated"]:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"Row {i+1}: {error_msg}. Data: {row}")
            except Exception as e:
                error_count += 1
                errors.append(f"Row {i+1}: Processing error - {str(e)}. "
                              f"Data: {row}")

        # Update ingestion log status
        if error_count == 0:
            ingestion_log.status = "SUCCESS"
        elif success_count > 0:
            ingestion_log.status = "PARTIAL_SUCCESS"
        else:
            ingestion_log.status = "FAILED"
        ingestion_log.error_description = "\n".join(errors) if errors else None
        db.add(ingestion_log)  # "update" the log entry
        db.commit()

        return jsonify({
            "status": "success",
            "log_id": log_id,
            "success_count": success_count,
            "error_count": error_count,
            "errors_summary": errors if errors else "No errors"
        }), 200

    except base64.binascii.Error:
        db.rollback()
        ingestion_log.status = "FAILED"
        ingestion_log.error_description = "Invalid base64 encoding"
        db.add(ingestion_log)
        db.commit()
        return jsonify({"error": "Invalid base64 encoding"}), 400
    except csv.Error as e:
        db.rollback()
        ingestion_log.status = "FAILED"
        ingestion_log.error_description = f"CSV parsing error: {str(e)}"
        db.add(ingestion_log)
        db.commit()
        return jsonify({"error": f"CSV parsing error: {str(e)}"}), 400
    except SQLAlchemyError as e:  # Catch database errors
        db.rollback()
        ingestion_log.status = "FAILED"
        ingestion_log.error_description = \
            f"Database error during upload: {str(e)}"
        db.add(ingestion_log)
        db.commit()
        return jsonify({"error": f"Database error during upload: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        ingestion_log.status = "FAILED"
        ingestion_log.error_description = \
            f"An unexpected error occurred: {str(e)}"
        db.add(ingestion_log)
        db.commit()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@admin_portal_bp.route('/campaigns/moengage-export', methods=['GET'])
def download_moengage_file():
    """
    Generates and allows download of the Moengage format CSV file for campaigns.
    (FR31, FR44)
    """
    try:
        # In a real scenario, this would involve complex queries,
        # DND checks (FR23), and offer selection logic.
        # For mock, we'll generate sample data.
        # Assume a service provides the data ready for Moengage.

        # Example data structure for Moengage (simplified)
        # This should align with Moengage's expected format.
        # FR44: generate in .csv format, uploadable in Moengage.
        moengage_data = [
            {"customer_id": str(uuid.uuid4()), "mobile": "9876543210",
             "offer_code": "LOAN001", "campaign_segment": "C1",
             "propensity_score": "High"},
            {"customer_id": str(uuid.uuid4()), "mobile": "9876543211",
             "offer_code": "LOAN002", "campaign_segment": "C2",
             "propensity_score": "Medium"}
        ]

        # Filter out DND customers (FR23) - mock implementation
        # In a real system, this would query the customer table's dnd_flag
        # or a dedicated DND list.
        # For now, assume moengage_data already respects DND.

        output = io.StringIO()
        fieldnames = moengage_data[0].keys() if moengage_data else []
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(moengage_data)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='moengage_campaign_data.csv'
        )
    except Exception as e:
        return jsonify(
            {"error": f"Failed to generate Moengage file: {str(e)}"}
        ), 500


@admin_portal_bp.route('/data/duplicates', methods=['GET'])
def download_duplicate_data():
    """
    Allows download of a file containing identified duplicate customer records.
    (FR32)
    """
    try:
        # This would query the database for identified duplicates.
        # The deduplication engine would likely maintain a log or flag
        # for duplicate entries.
        duplicate_records = deduplication_service.get_duplicate_records()

        output = io.StringIO()
        fieldnames = duplicate_records[0].keys() if duplicate_records else []
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(duplicate_records)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='duplicate_customer_data.csv'
        )
    except Exception as e:
        return jsonify(
            {"error": f"Failed to retrieve duplicate data: {str(e)}"}
        ), 500


@admin_portal_bp.route('/data/unique', methods=['GET'])
def download_unique_data():
    """
    Allows download of a file containing unique customer records after
    deduplication. (FR33)
    """
    try:
        # This would query the database for unique customer records.
        unique_records = deduplication_service.get_unique_records()

        output = io.StringIO()
        fieldnames = unique_records[0].keys() if unique_records else []
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(unique_records)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='unique_customer_data.csv'
        )
    except Exception as e:
        return jsonify(
            {"error": f"Failed to retrieve unique data: {str(e)}"}
        ), 500


@admin_portal_bp.route('/data/errors', methods=['GET'])
def download_error_file():
    """
    Allows download of an Excel file detailing errors from data ingestion
    processes. (FR34, FR38)
    Note: For simplicity, this implementation returns a CSV.
    For a true Excel file (.xlsx), a library like `openpyxl` would be needed.
    """
    try:
        # Query ingestion_logs for failed/partial uploads
        # In a real system, you might filter by date, log_id, etc.
        error_logs = [
            log.to_dict() for log in db.query(MockIngestionLog)
            if log.status in ["FAILED", "PARTIAL_SUCCESS"]
        ]

        output = io.StringIO()
        fieldnames = error_logs[0].keys() if error_logs else \
            ['log_id', 'file_name', 'upload_timestamp', 'status',
             'error_description']
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(error_logs)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',  # Changed from application/vnd.ms-excel
            as_attachment=True,
            download_name='data_ingestion_errors.csv'  # Changed from .xlsx
        )
    except Exception as e:
        return jsonify(
            {"error": f"Failed to retrieve error data: {str(e)}"}
        ), 500


@admin_portal_bp.route('/reports/daily-tally', methods=['GET'])
def get_daily_tally_report():
    """
    Provides a front-end for daily reports for data tally. (FR39)
    """
    # This would query aggregated data from customer, offer, and event tables
    # to provide counts for new customers, updated offers, events, etc.
    # The specific format is ambiguous (Q13).
    try:
        # Mock data for daily tally
        report_date = request.args.get(
            'date', datetime.now().strftime('%Y-%m-%d')
        )
        total_customers = len(db.query(MockCustomer))
        new_customers_today = 50  # Placeholder
        offers_updated_today = 120  # Placeholder
        events_recorded_today = 500  # Placeholder

        report_data = {
            "report_date": report_date,
            "total_customers_in_cdp": total_customers,
            "new_customers_ingested_today": new_customers_today,
            "offers_updated_today": offers_updated_today,
            "events_recorded_today": events_recorded_today,
            "status": "success",
            "message": "Daily data tally report generated successfully."
        }
        return jsonify(report_data), 200
    except Exception as e:
        return jsonify(
            {"error": f"Failed to generate daily tally report: {str(e)}"}
        ), 500


@admin_portal_bp.route('/reports/customer-view/<customer_id>', methods=['GET'])
def get_customer_level_view(customer_id):
    """
    Provides a front-end for customer-level view with stages. (FR40)
    This is similar to the /customers/{customer_id} endpoint in system design,
    but explicitly for admin portal reporting.
    """
    try:
        customer = db.get_customer_by_identifiers(customer_id=customer_id)
        if not customer:
            return jsonify({"error": "Customer not found"}), 404

        # In a real system, fetch associated offers and events from DB
        # For mock, provide sample data
        customer_offers = [
            o.to_dict() for o in db.offers.values()
            if o.customer_id == customer_id
        ]
        customer_events = [
            {"event_type": "LOAN_LOGIN",
             "event_timestamp": "2023-10-26T10:00:00Z",
             "source": "LOS"},
            {"event_type": "EKYC_ACHIEVED",
             "event_timestamp": "2023-10-26T10:30:00Z",
             "source": "LOS"},
            {"event_type": "SMS_DELIVERED",
             "event_timestamp": "2023-10-25T09:00:00Z",
             "source": "Moengage"}
        ]

        customer_data = customer.to_dict()
        customer_data["current_offers"] = customer_offers
        customer_data["journey_stages"] = customer_events

        return jsonify(customer_data), 200
    except Exception as e:
        return jsonify(
            {"error": f"Failed to retrieve customer view: {str(e)}"}
        ), 500