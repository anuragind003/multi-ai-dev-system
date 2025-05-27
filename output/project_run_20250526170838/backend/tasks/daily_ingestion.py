import logging
import uuid
from datetime import datetime, date
from sqlalchemy.exc import SQLAlchemyError

# Assuming db is initialized in backend.app and models are defined in backend.models
# In a real Flask application, these would be imported as:
# from backend.app import db
# from backend.models import Customer, Offer, IngestionLog

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Placeholder for actual imports (for standalone testing) ---
# These will be replaced by actual imports when integrated into the Flask app.
# For the purpose of providing a complete, runnable file, we define minimal mocks.
try:
    from backend.app import db
    from backend.models import Customer, Offer, IngestionLog
except ImportError:
    logger.warning("Could not import db or models from backend.app/backend.models. "
                   "Using mock definitions for standalone execution. "
                   "Ensure these are correctly set up in your Flask application.")
    # Minimal mock definitions for standalone execution/testing
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy

    app = Flask(__name__)
    # Use an in-memory SQLite for testing if PostgreSQL is not readily available
    # For actual deployment, use the PostgreSQL URI
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    class Customer(db.Model):
        __tablename__ = 'customers'
        customer_id = db.Column(db.Text, primary_key=True)
        mobile_number = db.Column(db.Text, unique=True)
        pan_number = db.Column(db.Text, unique=True)
        aadhaar_number = db.Column(db.Text, unique=True)
        ucid_number = db.Column(db.Text, unique=True)
        loan_application_number = db.Column(db.Text, unique=True)
        dnd_flag = db.Column(db.Boolean, default=False)
        segment = db.Column(db.Text)
        created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
        updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    class Offer(db.Model):
        __tablename__ = 'offers'
        offer_id = db.Column(db.Text, primary_key=True)
        customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
        offer_type = db.Column(db.Text)
        offer_status = db.Column(db.Text)
        propensity = db.Column(db.Text)
        start_date = db.Column(db.Date)
        end_date = db.Column(db.Date)
        channel = db.Column(db.Text)
        created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
        updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
        customer = db.relationship('Customer', backref=db.backref('offers', lazy=True))

    class IngestionLog(db.Model):
        __tablename__ = 'ingestion_logs'
        log_id = db.Column(db.Text, primary_key=True)
        file_name = db.Column(db.Text, nullable=False)
        upload_timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow)
        status = db.Column(db.Text)
        error_description = db.Column(db.Text)

    # This is a hack to make the `if __name__ == "__main__":` block runnable
    # by ensuring `db` and models are available in the current scope.
    # In a real Flask app, this would not be necessary.
    import sys
    sys.modules['backend.app'] = type('module', (object,), {'db': db})
    sys.modules['backend.models'] = type('module', (object,), {'Customer': Customer, 'Offer': Offer, 'IngestionLog': IngestionLog})
# --- End Placeholder ---


def _simulate_offermart_data_read() -> list[dict]:
    """
    Simulates reading daily customer and offer data from an Offermart staging area.
    In a real scenario, this would read from a file (CSV/Parquet), a message queue,
    or a dedicated staging database table.
    Returns a list of dictionaries, each representing a row of incoming data.
    """
    logger.info("Simulating reading data from Offermart staging area...")
    # Mock data based on expected fields from BRD and schema
    mock_data = [
        {
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhaar_number": "123456789012",
            "ucid_number": "UCID001",
            "loan_application_number": None,
            "dnd_flag": False,
            "segment": "C1",
            "offer_id": "OFFER001",
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity": "High",
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "channel": "E-aggregator"
        },
        {
            "mobile_number": "9876543211",
            "pan_number": "FGHIJ5678K",
            "aadhaar_number": "234567890123",
            "ucid_number": "UCID002",
            "loan_application_number": None,
            "dnd_flag": False,
            "segment": "C2",
            "offer_id": "OFFER002",
            "offer_type": "Enrich",
            "offer_status": "Active",
            "propensity": "Medium",
            "start_date": "2023-02-01",
            "end_date": "2024-11-30",
            "channel": "Loyalty"
        },
        {
            "mobile_number": "9876543210",  # Duplicate mobile number
            "pan_number": "ABCDE1234F",  # Duplicate PAN
            "aadhaar_number": "123456789012",  # Duplicate Aadhaar
            "ucid_number": "UCID001",  # Duplicate UCID
            "loan_application_number": None,
            "dnd_flag": False,
            "segment": "C1_Updated",  # Update segment
            "offer_id": "OFFER003",  # New offer for existing customer
            "offer_type": "New-new",
            "offer_status": "Active",
            "propensity": "Very High",
            "start_date": "2024-03-01",
            "end_date": "2024-09-30",
            "channel": "Insta"
        },
        {
            "mobile_number": "9999999999",
            "pan_number": "LMNOP9012Q",
            "aadhaar_number": "345678901234",
            "ucid_number": "UCID003",
            "loan_application_number": "LAN001",  # Customer with a loan application
            "dnd_flag": True,  # DND customer
            "segment": "C3",
            "offer_id": "OFFER004",
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity": "Low",
            "start_date": "2024-01-15",
            "end_date": "2024-07-15",
            "channel": "E-aggregator"
        },
        {
            "mobile_number": "1111111111",
            "pan_number": "RSTUV3456W",
            "aadhaar_number": "456789012345",
            "ucid_number": "UCID004",
            "loan_application_number": None,
            "dnd_flag": False,
            "segment": "C4",
            "offer_id": "OFFER005",
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity": "Medium",
            "start_date": "2023-01-01",
            "end_date": "2023-01-01",  # Offer that should expire (for testing expiry logic)
            "channel": "Loyalty"
        }
    ]
    logger.info(f"Simulated {len(mock_data)} records from Offermart.")
    return mock_data


def _validate_offermart_data_row(row_data: dict) -> tuple[bool, str]:
    """
    Performs basic column-level validation on a single row of Offermart data.
    FR1: The system shall perform basic column-level validation.
    """
    required_fields = [
        "mobile_number", "pan_number", "aadhaar_number", "ucid_number",
        "offer_id", "offer_type", "offer_status", "propensity",
        "start_date", "end_date", "channel"
    ]
    for field in required_fields:
        if field not in row_data or not row_data[field]:
            return False, f"Missing or empty required field: {field}"

    # Basic format validation (e.g., mobile number length, date format)
    if not isinstance(row_data["mobile_number"], str) or len(row_data["mobile_number"]) != 10:
        return False, "Invalid mobile_number format or length (expected 10 digits)."
    if not isinstance(row_data["pan_number"], str) or len(row_data["pan_number"]) != 10:
        return False, "Invalid pan_number format or length (expected 10 chars)."
    if not isinstance(row_data["aadhaar_number"], str) or len(row_data["aadhaar_number"]) != 12:
        return False, "Invalid aadhaar_number format or length (expected 12 digits)."

    try:
        datetime.strptime(row_data["start_date"], "%Y-%m-%d").date()
        datetime.strptime(row_data["end_date"], "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format. Expected YYYY-MM-DD."

    if row_data["offer_status"] not in ["Active", "Inactive", "Expired"]:
        return False, "Invalid offer_status. Must be 'Active', 'Inactive', or 'Expired'."

    return True, "Validation successful"


def _process_single_record(record: dict) -> tuple[bool, str, str]:
    """
    Processes a single record from the Offermart staging area.
    Handles customer deduplication and offer creation/update.
    FR3, FR4, FR5 (partially), FR6, FR8.
    Returns (success_status, customer_id, message)
    """
    try:
        # Extract customer identifying fields
        mobile_number = record.get("mobile_number")
        pan_number = record.get("pan_number")
        aadhaar_number = record.get("aadhaar_number")
        ucid_number = record.get("ucid_number")
        loan_application_number = record.get("loan_application_number")
        offer_id = record.get("offer_id")

        # Deduplication logic: Find existing customer
        # FR3: Deduplicate based on Mobile, PAN, Aadhaar, UCID, or previous loan application number.
        customer = None
        if mobile_number:
            customer = Customer.query.filter_by(mobile_number=mobile_number).first()
        if not customer and pan_number:
            customer = Customer.query.filter_by(pan_number=pan_number).first()
        if not customer and aadhaar_number:
            customer = Customer.query.filter_by(aadhaar_number=aadhaar_number).first()
        if not customer and ucid_number:
            customer = Customer.query.filter_by(ucid_number=ucid_number).first()
        if not customer and loan_application_number:
            customer = Customer.query.filter_by(loan_application_number=loan_application_number).first()

        if customer:
            # Update existing customer details
            logger.info(f"Customer with ID {customer.customer_id} found. Updating details.")
            customer.mobile_number = mobile_number or customer.mobile_number
            customer.pan_number = pan_number or customer.pan_number
            customer.aadhaar_number = aadhaar_number or customer.aadhaar_number
            customer.ucid_number = ucid_number or customer.ucid_number
            customer.loan_application_number = loan_application_number or customer.loan_application_number
            customer.dnd_flag = record.get("dnd_flag", customer.dnd_flag)
            customer.segment = record.get("segment", customer.segment)
            customer.updated_at = datetime.utcnow()
        else:
            # Create new customer
            customer_id = str(uuid.uuid4())
            customer = Customer(
                customer_id=customer_id,
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_number=aadhaar_number,
                ucid_number=ucid_number,
                loan_application_number=loan_application_number,
                dnd_flag=record.get("dnd_flag", False),
                segment=record.get("segment"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(customer)
            logger.info(f"New customer created with ID: {customer.customer_id}")

        # Process Offer data
        offer = Offer.query.filter_by(offer_id=offer_id).first()
        if offer:
            # FR8: Update old offers in Analytics Offermart with new data received from CDP
            # (This means updating existing offers in CDP based on incoming data)
            logger.info(f"Offer with ID {offer_id} found for customer {customer.customer_id}. Updating offer details.")
            offer.customer_id = customer.customer_id  # Ensure offer is linked to the correct (deduplicated) customer
            offer.offer_type = record.get("offer_type", offer.offer_type)
            offer.offer_status = record.get("offer_status", offer.offer_status)
            offer.propensity = record.get("propensity", offer.propensity)
            offer.start_date = datetime.strptime(record["start_date"], "%Y-%m-%d").date()
            offer.end_date = datetime.strptime(record["end_date"], "%Y-%m-%d").date()
            offer.channel = record.get("channel", offer.channel)
            offer.updated_at = datetime.utcnow()
        else:
            # Create new offer
            offer = Offer(
                offer_id=offer_id,
                customer_id=customer.customer_id,
                offer_type=record.get("offer_type"),
                offer_status=record.get("offer_status"),
                propensity=record.get("propensity"),
                start_date=datetime.strptime(record["start_date"], "%Y-%m-%d").date(),
                end_date=datetime.strptime(record["end_date"], "%Y-%m-%d").date(),
                channel=record.get("channel"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(offer)
            logger.info(f"New offer created with ID: {offer.offer_id} for customer {customer.customer_id}")

        return True, customer.customer_id, "Record processed successfully."

    except SQLAlchemyError as e:
        logger.error(f"Database error processing record {record.get('offer_id')}: {e}")
        # No rollback here, as the main task will handle the session commit/rollback
        return False, None, f"Database error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error processing record {record.get('offer_id')}: {e}")
        return False, None, f"Processing error: {e}"


def _update_expired_offers():
    """
    Updates the status of offers that have expired.
    FR41: Mark offers as expired based on offer end dates for non-journey started customers.
    FR43: Mark offers as expired for journey started customers whose LAN (Loan Application Number) validity is over.
    (Note: FR42 - replenishing new offers - is out of scope for this specific task's complexity,
    as it requires business logic for offer generation.)
    """
    logger.info("Starting offer expiry status update...")
    today = date.today()
    updated_count = 0

    try:
        # FR41: Mark offers as expired based on offer end dates for non-journey started customers.
        # Assuming 'non-journey started' means customer.loan_application_number is NULL or empty.
        offers_to_expire_non_journey = Offer.query.join(Customer).filter(
            Offer.end_date < today,
            Offer.offer_status == 'Active',
            (Customer.loan_application_number.is_(None) | (Customer.loan_application_number == ''))
        ).all()

        for offer in offers_to_expire_non_journey:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            updated_count += 1
            logger.info(f"Offer {offer.offer_id} for customer {offer.customer_id} marked as 'Expired' (non-journey).")

        # FR43: Mark offers as expired for journey started customers whose LAN (Loan Application Number) validity is over.
        # Assumption: "LAN validity is over" means the associated offer's end_date is past.
        # In a real system, LAN validity might be a separate field or determined by LOS.
        # For simplicity, we'll use offer.end_date for journey-started customers too.
        offers_to_expire_journey = Offer.query.join(Customer).filter(
            Offer.end_date < today,
            Offer.offer_status == 'Active',
            Customer.loan_application_number.isnot(None),
            Customer.loan_application_number != ''
        ).all()

        for offer in offers_to_expire_journey:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            updated_count += 1
            logger.info(f"Offer {offer.offer_id} for customer {offer.customer_id} marked as 'Expired' (journey started).")

        db.session.commit()
        logger.info(f"Completed offer expiry status update. {updated_count} offers marked as 'Expired'.")

    except SQLAlchemyError as e:
        logger.error(f"Database error during offer expiry update: {e}")
        db.session.rollback()
    except Exception as e:
        logger.error(f"Unexpected error during offer expiry update: {e}")


def daily_ingestion_task():
    """
    Main function to orchestrate the daily data ingestion from Offermart.
    This function should be scheduled to run daily.
    FR9: Receive Offer and Customer data from Offermart daily.
    NFR5: Process daily data pushes from Offermart.
    """
    logger.info("Starting daily Offermart data ingestion task...")
    start_time = datetime.utcnow()
    total_records = 0
    processed_success = 0
    processed_errors = 0
    error_details = []
    status = "FAILED" # Default status

    try:
        offermart_data = _simulate_offermart_data_read()
        total_records = len(offermart_data)

        for i, record in enumerate(offermart_data):
            logger.info(f"Processing record {i+1}/{total_records}...")
            is_valid, validation_msg = _validate_offermart_data_row(record)

            if not is_valid:
                logger.warning(f"Record {i+1} failed validation: {validation_msg}. Data: {record}")
                error_details.append(f"Record {i+1} (Offer ID: {record.get('offer_id')}): Validation Error - {validation_msg}")
                processed_errors += 1
                continue

            success, customer_id, message = _process_single_record(record)
            if success:
                processed_success += 1
                logger.info(f"Successfully processed record for customer {customer_id}. Message: {message}")
            else:
                processed_errors += 1
                error_details.append(f"Record {i+1} (Offer ID: {record.get('offer_id')}): Processing Error - {message}")
                logger.error(f"Failed to process record {i+1}. Message: {message}. Data: {record}")

        # Commit all changes after processing all records
        db.session.commit()
        logger.info("All records processed and committed to database.")

        # Run offer expiry logic after ingestion
        _update_expired_offers()

        status = "SUCCESS" if processed_errors == 0 else "PARTIAL_SUCCESS"
        log_message = (f"Daily ingestion completed. Total: {total_records}, "
                       f"Success: {processed_success}, Errors: {processed_errors}.")
        logger.info(log_message)

    except Exception as e:
        db.session.rollback()
        status = "FAILED"
        log_message = f"Daily ingestion failed due to an unexpected error: {e}"
        logger.exception(log_message)
        error_details.append(f"Overall task failure: {e}")

    finally:
        # Log the ingestion attempt in the ingestion_logs table
        log_entry = IngestionLog(
            log_id=str(uuid.uuid4()),
            file_name="Offermart_Daily_Ingestion",  # Or actual file name if reading from a file
            upload_timestamp=start_time,
            status=status,
            error_description="\n".join(error_details) if error_details else None
        )
        db.session.add(log_entry)
        try:
            db.session.commit()
            logger.info(f"Ingestion log entry created with status: {status}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to commit ingestion log entry: {e}")
            db.session.rollback()  # Rollback log entry if it fails


if __name__ == "__main__":
    # This block is for local testing/demonstration purposes.
    # In a real Flask app, you'd typically run this via a Flask CLI command
    # or a scheduler like APScheduler integrated with your Flask app context.
    # To run this, ensure your database is configured and accessible.

    # If running standalone, the mock `app` and `db` from the `try-except` block above are used.
    # For a real PostgreSQL setup, change app.config['SQLALCHEMY_DATABASE_URI']
    # to your PostgreSQL connection string.
    with app.app_context():
        # Create tables if they don't exist (for testing purposes)
        db.create_all()
        print("Database tables created (if not existing).")

        # Clear existing data for a clean test run
        try:
            db.session.query(Offer).delete()
            db.session.query(Customer).delete()
            db.session.query(IngestionLog).delete()
            db.session.commit()
            print("Cleared existing customer, offer, and ingestion log data for testing.")
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing data: {e}")

        daily_ingestion_task()
        print("\nDaily ingestion task finished. Check logs above.")

        # Verify data in DB (optional)
        print("\n--- Current Customers in DB ---")
        for cust in Customer.query.all():
            print(f"ID: {cust.customer_id}, Mobile: {cust.mobile_number}, Segment: {cust.segment}, DND: {cust.dnd_flag}")

        print("\n--- Current Offers in DB ---")
        for offer in Offer.query.all():
            print(f"ID: {offer.offer_id}, Cust ID: {offer.customer_id}, Status: {offer.offer_status}, "
                  f"Start Date: {offer.start_date}, End Date: {offer.end_date}")

        print("\n--- Ingestion Logs ---")
        for log in IngestionLog.query.all():
            print(f"Log ID: {log.log_id}, File: {log.file_name}, Status: {log.status}, "
                  f"Errors: {log.error_description if log.error_description else 'None'}")