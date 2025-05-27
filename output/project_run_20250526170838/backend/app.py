import os
import uuid
import base64
import io
import csv
from datetime import datetime, date

from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text

# Initialize Flask app
app = Flask(__name__)

# Configuration
# Use environment variables for sensitive data like database URI
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://user:password@localhost:5432/cdp_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database Models
# All primary keys and foreign keys should be UUIDs, represented as TEXT in DDL.
# Using SQLAlchemy's UUID type for better type handling.


class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.Text, unique=True, nullable=True)
    pan_number = db.Column(db.Text, unique=True, nullable=True)
    aadhaar_number = db.Column(db.Text, unique=True, nullable=True)
    ucid_number = db.Column(db.Text, unique=True, nullable=True)
    loan_application_number = db.Column(db.Text, unique=True, nullable=True)
    dnd_flag = db.Column(db.Boolean, default=False)
    segment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    offers = db.relationship('Offer', backref='customer', lazy=True)
    events = db.relationship('Event', backref='customer', lazy=True)


class Offer(db.Model):
    __tablename__ = 'offers'
    offer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.Text)  # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.Text)  # 'Active', 'Inactive', 'Expired'
    propensity = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    channel = db.Column(db.Text)  # For attribution logic
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Event(db.Model):
    __tablename__ = 'events'
    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.Text)  # 'SMS_SENT', 'SMS_DELIVERED', 'EKYC_ACHIEVED', 'LOAN_LOGIN', etc.
    event_source = db.Column(db.Text)  # 'Moengage', 'LOS', 'E-aggregator'
    event_timestamp = db.Column(db.DateTime)
    event_details = db.Column(db.JSONB)  # Flexible storage for event-specific data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CampaignMetric(db.Model):
    __tablename__ = 'campaign_metrics'
    metric_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_unique_id = db.Column(db.Text, unique=True, nullable=False)
    campaign_name = db.Column(db.Text)
    campaign_date = db.Column(db.Date)
    attempted_count = db.Column(db.Integer)
    sent_success_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    conversion_rate = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IngestionLog(db.Model):
    __tablename__ = 'ingestion_logs'
    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = db.Column(db.Text, nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Text)  # 'SUCCESS', 'FAILED', 'PROCESSING'
    error_description = db.Column(db.Text)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)


# Helper function for deduplication (simplified for MVP)
def find_or_create_customer(data):
    """
    Finds an existing customer based on unique identifiers or creates a new one.
    Deduplication logic (FR3, FR4, FR5, FR6) is simplified for MVP.
    """
    mobile = data.get('mobile_number')
    pan = data.get('pan_number')
    aadhaar = data.get('aadhaar_number')
    ucid = data.get('ucid_number')
    loan_app_num = data.get('loan_application_number')

    customer = None

    # Prioritized search for existing customer
    if mobile:
        customer = Customer.query.filter_by(mobile_number=mobile).first()
    if not customer and pan:
        customer = Customer.query.filter_by(pan_number=pan).first()
    if not customer and aadhaar:
        customer = Customer.query.filter_by(aadhaar_number=aadhaar).first()
    if not customer and ucid:
        customer = Customer.query.filter_by(ucid_number=ucid).first()
    if not customer and loan_app_num:
        customer = Customer.query.filter_by(loan_application_number=loan_app_num).first()

    if customer:
        # Update existing customer data if new data is more complete
        if mobile and not customer.mobile_number:
            customer.mobile_number = mobile
        if pan and not customer.pan_number:
            customer.pan_number = pan
        if aadhaar and not customer.aadhaar_number:
            customer.aadhaar_number = aadhaar
        if ucid and not customer.ucid_number:
            customer.ucid_number = ucid
        if loan_app_num and not customer.loan_application_number:
            customer.loan_application_number = loan_app_num
        # Update segment or DND if provided
        if data.get('segment'):
            customer.segment = data['segment']
        if 'dnd_flag' in data:
            customer.dnd_flag = data['dnd_flag']
        db.session.add(customer)
        return customer, False  # Existing customer, not new
    else:
        # Create new customer
        new_customer = Customer(
            mobile_number=mobile,
            pan_number=pan,
            aadhaar_number=aadhaar,
            ucid_number=ucid,
            loan_application_number=loan_app_num,
            segment=data.get('segment'),
            dnd_flag=data.get('dnd_flag', False)
        )
        db.session.add(new_customer)
        return new_customer, True  # New customer


# API Endpoints

@app.route('/api/leads', methods=['POST'])
def receive_lead_data():
    """
    Receives real-time lead generation data from Insta/E-aggregators and inserts into CDP.
    FR7, FR11, FR12.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    required_fields = ['mobile_number', 'loan_type', 'source_channel']
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        customer, is_new = find_or_create_customer(data)
        db.session.commit()

        # Create an event for lead generation
        event = Event(
            customer_id=customer.customer_id,
            event_type='LEAD_GENERATED',
            event_source=data.get('source_channel'),
            event_timestamp=datetime.utcnow(),
            event_details={
                'loan_type': data.get('loan_type'),
                'source_channel': data.get('source_channel')
            }
        )
        db.session.add(event)
        db.session.commit()

        return jsonify({
            "status": "success",
            "customer_id": str(customer.customer_id),
            "message": "Customer lead processed successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error processing lead data: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/api/eligibility', methods=['POST'])
def receive_eligibility_data():
    """
    Receives real-time eligibility data from Insta/E-aggregators and updates customer/offer data.
    FR7, FR11, FR12.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    required_fields = ['customer_id', 'offer_id', 'eligibility_status', 'loan_amount']
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        customer = Customer.query.get(data['customer_id'])
        offer = Offer.query.get(data['offer_id'])

        if not customer:
            return jsonify({"status": "error", "message": "Customer not found"}), 404
        if not offer or offer.customer_id != customer.customer_id:
            return jsonify({"status": "error", "message": "Offer not found or does not belong to customer"}), 404

        # Update offer status based on eligibility
        offer.offer_status = data['eligibility_status']
        offer.updated_at = datetime.utcnow()
        db.session.add(offer)

        # Create an event for eligibility update
        event = Event(
            customer_id=customer.customer_id,
            event_type='ELIGIBILITY_UPDATE',
            event_source=data.get('source', 'E-aggregator'),
            event_timestamp=datetime.utcnow(),
            event_details={
                'offer_id': str(offer.offer_id),
                'eligibility_status': data['eligibility_status'],
                'loan_amount': data['loan_amount']
            }
        )
        db.session.add(event)
        db.session.commit()

        return jsonify({"status": "success", "message": "Eligibility updated"}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error processing eligibility data: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/api/status-updates', methods=['POST'])
def receive_status_updates():
    """
    Receives real-time application status updates from Insta/E-aggregators or LOS.
    FR25, FR26.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    required_fields = ['customer_id', 'current_stage', 'status_timestamp']
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        customer = Customer.query.get(data['customer_id'])
        if not customer:
            return jsonify({"status": "error", "message": "Customer not found"}), 404

        # Convert status_timestamp to datetime object
        status_timestamp = datetime.fromisoformat(data['status_timestamp'])

        # Create an event for status update
        event = Event(
            customer_id=customer.customer_id,
            event_type=f"APP_STAGE_{data['current_stage'].upper()}",
            event_source=data.get('source', 'LOS'),
            event_timestamp=status_timestamp,
            event_details={
                'loan_application_number': data.get('loan_application_number'),
                'current_stage': data['current_stage']
            }
        )
        db.session.add(event)

        # FR14: Prevent modification of customer offers with a started loan application journey
        # This logic would be more complex, potentially involving a check on the offer status
        # and the loan_application_number associated with the offer.
        # For now, we just record the event.
        db.session.commit()

        return jsonify({"status": "success", "message": "Status updated"}), 200
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid status_timestamp format"}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error processing status update: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/admin/customer-data/upload', methods=['POST'])
def upload_customer_data():
    """
    Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans) via Admin Portal.
    FR35, FR36, FR37, FR38.
    """
    data = request.get_json()
    if not data or 'file_content' not in data or 'file_name' not in data or 'loan_type' not in data:
        return jsonify({"status": "error", "message": "Missing file_content, file_name, or loan_type"}), 400

    file_content_b64 = data['file_content']
    file_name = data['file_name']
    loan_type = data['loan_type']

    log_entry = IngestionLog(
        file_name=file_name,
        status='PROCESSING',
        error_description=None
    )
    db.session.add(log_entry)
    db.session.commit()  # Commit to get log_id

    try:
        decoded_content = base64.b64decode(file_content_b64).decode('utf-8')
        csv_file = io.StringIO(decoded_content)
        reader = csv.DictReader(csv_file)

        success_count = 0
        error_count = 0
        errors = []

        # Basic column-level validation (FR1) - check for presence of key columns
        expected_headers = ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number']
        if not any(header in reader.fieldnames for header in expected_headers):
            raise ValueError(
                "CSV missing expected identifiers: mobile_number, pan_number, aadhaar_number, or ucid_number"
            )

        for row_num, row in enumerate(reader, start=2):  # Start from 2 for header + first data row
            try:
                # Prepare data for deduplication
                customer_data = {
                    'mobile_number': row.get('mobile_number'),
                    'pan_number': row.get('pan_number'),
                    'aadhaar_number': row.get('aadhaar_number'),
                    'ucid_number': row.get('ucid_number'),
                    'loan_application_number': row.get('loan_application_number'),
                    'segment': row.get('segment'),
                    'dnd_flag': row.get('dnd_flag', 'FALSE').upper() == 'TRUE'
                }

                # Basic validation: at least one identifier must be present
                if not any(customer_data[key] for key in expected_headers):
                    raise ValueError("Row must contain at least one identifier (mobile, PAN, Aadhaar, UCID)")

                customer, is_new = find_or_create_customer(customer_data)
                db.session.add(customer)  # Add or re-add updated customer

                # If it's a new lead, generate an event
                if is_new:
                    event = Event(
                        customer_id=customer.customer_id,
                        event_type='LEAD_GENERATED_UPLOAD',
                        event_source='AdminPortal_Upload',
                        event_timestamp=datetime.utcnow(),
                        event_details={'loan_type': loan_type, 'file_name': file_name}
                    )
                    db.session.add(event)

                success_count += 1
            except Exception as row_e:
                error_count += 1
                errors.append(f"Row {row_num}: {row_e} - Data: {row}")
                app.logger.warning(f"Error processing row {row_num} in {file_name}: {row_e}")

        log_entry.status = 'SUCCESS' if not errors else 'PARTIAL_SUCCESS'
        log_entry.error_description = "\n".join(errors) if errors else None
        log_entry.success_count = success_count
        log_entry.error_count = error_count
        db.session.commit()

        return jsonify({
            "status": "success",
            "log_id": str(log_entry.log_id),
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }), 200

    except Exception as e:
        db.session.rollback()
        log_entry.status = 'FAILED'
        log_entry.error_description = f"File processing failed: {e}"
        db.session.commit()
        app.logger.error(f"Error uploading customer data file {file_name}: {e}")
        return jsonify({"status": "error", "message": f"File upload failed: {e}"}), 500


@app.route('/customers/<uuid:customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    """
    Retrieves a single customer's profile view with associated offers and journey stages.
    FR2, FR40.
    """
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"status": "error", "message": "Customer not found"}), 404

    offers_data = []
    for offer in customer.offers:
        offers_data.append({
            "offer_id": str(offer.offer_id),
            "offer_type": offer.offer_type,
            "offer_status": offer.offer_status,
            "propensity": offer.propensity,
            "start_date": offer.start_date.isoformat() if offer.start_date else None,
            "end_date": offer.end_date.isoformat() if offer.end_date else None,
            "channel": offer.channel
        })

    journey_stages_data = []
    for event in customer.events.order_by(Event.event_timestamp).all():
        journey_stages_data.append({
            "event_type": event.event_type,
            "event_timestamp": event.event_timestamp.isoformat(),
            "source": event.event_source,
            "details": event.event_details
        })

    customer_profile = {
        "customer_id": str(customer.customer_id),
        "mobile_number": customer.mobile_number,
        "pan_number": customer.pan_number,
        "aadhaar_number": customer.aadhaar_number,
        "ucid_number": customer.ucid_number,
        "loan_application_number": customer.loan_application_number,
        "dnd_flag": customer.dnd_flag,
        "segment": customer.segment,
        "current_offers": offers_data,
        "journey_stages": journey_stages_data
    }

    return jsonify({"status": "success", "data": customer_profile}), 200


@app.route('/campaigns/moengage-export', methods=['GET'])
def export_moengage_file():
    """
    Generates and allows download of the Moengage format CSV file for campaigns.
    FR31, FR44.
    Excludes DND customers (FR23).
    """
    # For simplicity, let's export active offers for non-DND customers
    # A real scenario would involve more complex filtering based on campaign rules
    customers_for_campaign = db.session.query(Customer, Offer).join(Offer).filter(
        Customer.dnd_flag == False,  # noqa: E712 (False is literal, not variable)
        Offer.offer_status == 'Active'
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Moengage format headers (example, adjust as per actual Moengage requirements)
    headers = [
        'customer_id', 'mobile_number', 'pan_number', 'offer_id',
        'offer_type', 'offer_status', 'propensity', 'offer_end_date'
    ]
    writer.writerow(headers)

    for customer, offer in customers_for_campaign:
        row = [
            str(customer.customer_id),
            customer.mobile_number,
            customer.pan_number,
            str(offer.offer_id),
            offer.offer_type,
            offer.offer_status,
            offer.propensity,
            offer.end_date.isoformat() if offer.end_date else ''
        ]
        writer.writerow(row)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='moengage_campaign_data.csv'
    )


@app.route('/data/duplicates', methods=['GET'])
def download_duplicate_data():
    """
    Allows download of a file containing identified duplicate customer records.
    FR32.
    For MVP, this will be a simplified representation.
    A robust solution would involve a dedicated deduplication process
    that flags or stores duplicate groups.
    """
    # This is a placeholder. In a real system, duplicates would be identified
    # by a background process and stored, or identified on the fly with complex logic.
    # Given the current schema, unique constraints prevent direct duplicates.
    # This endpoint would typically query a 'deduplication_log' or similar table
    # that records potential duplicates before resolution, or merged records.
    # For the MVP, we'll return a sample CSV.

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['original_customer_id', 'duplicate_customer_id', 'reason', 'merge_date'])
    writer.writerow(['mock_uuid_1', 'mock_uuid_2', 'Same Mobile Number', '2023-01-15'])
    writer.writerow(['mock_uuid_3', 'mock_uuid_4', 'Same PAN Number', '2023-02-20'])
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='duplicate_customer_data.csv'
    )


@app.route('/data/unique', methods=['GET'])
def download_unique_data():
    """
    Allows download of a file containing unique customer records after deduplication.
    FR33.
    """
    customers = Customer.query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        'customer_id', 'mobile_number', 'pan_number', 'aadhaar_number',
        'ucid_number', 'loan_application_number', 'dnd_flag', 'segment',
        'created_at', 'updated_at'
    ]
    writer.writerow(headers)

    for customer in customers:
        row = [
            str(customer.customer_id),
            customer.mobile_number,
            customer.pan_number,
            customer.aadhaar_number,
            customer.ucid_number,
            customer.loan_application_number,
            customer.dnd_flag,
            customer.segment,
            customer.created_at.isoformat(),
            customer.updated_at.isoformat()
        ]
        writer.writerow(row)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='unique_customer_data.csv'
    )


@app.route('/data/errors', methods=['GET'])
def download_error_file():
    """
    Allows download of an Excel file (CSV for MVP) detailing errors from data ingestion processes.
    FR34, FR38.
    """
    error_logs = IngestionLog.query.filter(
        (IngestionLog.status == 'FAILED') | (IngestionLog.status == 'PARTIAL_SUCCESS')
    ).order_by(IngestionLog.upload_timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    headers = ['log_id', 'file_name', 'upload_timestamp', 'status', 'error_description']
    writer.writerow(headers)

    for log in error_logs:
        row = [
            str(log.log_id),
            log.file_name,
            log.upload_timestamp.isoformat(),
            log.status,
            log.error_description if log.error_description else ''
        ]
        writer.writerow(row)

    output.seek(0)
    # Although the BRD mentions "Error Excel file", for simplicity and
    # avoiding extra dependencies for MVP, we'll provide a CSV.
    # If a true Excel file is required, openpyxl would be needed.
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='data_ingestion_errors.csv'
    )


# Database initialization command for Flask CLI
@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    db.drop_all()
    db.create_all()
    print('Initialized the database.')


if __name__ == '__main__':
    # This block is for local development only.
    # In production, a WSGI server (e.g., Gunicorn) would run the app.
    # Ensure environment variables are set for DATABASE_URL and SECRET_KEY.
    app.run(debug=True, host='0.0.0.0', port=5000)