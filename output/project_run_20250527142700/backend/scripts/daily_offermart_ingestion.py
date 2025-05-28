import os
import csv
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError, OperationalError
import logging

# --- Configuration ---
# In a real application, this would be loaded from environment variables or a dedicated config file.
# For this script, we'll define it directly.
DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://user:password@localhost:5432/cdp_db')
OFFERMART_STAGING_FILE = os.getenv('OFFERMART_STAGING_FILE', 'data/offermart_daily_data.csv')

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- SQLAlchemy Setup ---
Base = declarative_base()
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

# --- Database Models (matching the provided schema) ---
class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True)
    pan_number = Column(String(10), unique=True)
    aadhaar_number = Column(String(12), unique=True)
    ucid_number = Column(String(50), unique=True)
    customer_360_id = Column(String(50))
    is_dnd = Column(Boolean, default=False)
    segment = Column(String(50))
    attributes = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Customer(id={self.customer_id}, mobile={self.mobile_number})>"

class Offer(Base):
    __tablename__ = 'offers'
    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    source_offer_id = Column(String(100)) # Original ID from Offermart/E-aggregator
    offer_type = Column(String(50)) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = Column(String(50)) # 'Active', 'Inactive', 'Expired'
    propensity = Column(String(50))
    loan_application_number = Column(String(100)) # LAN
    valid_until = Column(DateTime(timezone=True))
    source_system = Column(String(50)) # 'Offermart', 'E-aggregator'
    channel = Column(String(50)) # For attribution
    is_duplicate = Column(Boolean, default=False) # Flagged by deduplication
    original_offer_id = Column(UUID(as_uuid=True), ForeignKey('offers.offer_id')) # Points to the offer it duplicated/enriched
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Offer(id={self.offer_id}, customer_id={self.customer_id}, source_id={self.source_offer_id})>"

# Note: Other models (offer_history, events, campaigns) are not directly used by this ingestion script
# but would be defined similarly in a `models.py` file.

# --- Helper Functions ---

def get_db_session():
    """Provides a new SQLAlchemy session."""
    return Session()

def create_tables_if_not_exist():
    """Creates database tables based on models if they don't already exist."""
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables checked/created successfully.")
    except OperationalError as e:
        logger.error(f"Failed to connect to database or create tables: {e}")
        raise

def validate_offermart_row(row_data: dict, row_num: int) -> tuple[bool, dict, list]:
    """
    Performs basic column-level data validation for an Offermart row.
    Returns (is_valid, cleaned_data, errors).
    """
    errors = []
    cleaned_data = {}

    # Define expected columns and their types/validation rules
    expected_columns = {
        'mobile_number': {'required': True, 'type': str, 'max_len': 20},
        'pan_number': {'required': False, 'type': str, 'max_len': 10},
        'aadhaar_number': {'required': False, 'type': str, 'max_len': 12},
        'ucid_number': {'required': False, 'type': str, 'max_len': 50},
        'customer_360_id': {'required': False, 'type': str, 'max_len': 50},
        'is_dnd': {'required': False, 'type': bool},
        'segment': {'required': False, 'type': str, 'max_len': 50},
        'source_offer_id': {'required': True, 'type': str, 'max_len': 100},
        'offer_type': {'required': True, 'type': str, 'max_len': 50},
        'offer_status': {'required': True, 'type': str, 'max_len': 50},
        'propensity': {'required': False, 'type': str, 'max_len': 50},
        'loan_application_number': {'required': False, 'type': str, 'max_len': 100},
        'valid_until': {'required': True, 'type': datetime},
        'source_system': {'required': True, 'type': str, 'max_len': 50, 'default': 'Offermart'},
        'channel': {'required': False, 'type': str, 'max_len': 50},
        'attributes': {'required': False, 'type': dict} # For customer attributes
    }

    for col, rules in expected_columns.items():
        value = row_data.get(col)
        is_required = rules.get('required', False)
        expected_type = rules.get('type')
        max_len = rules.get('max_len')
        default_value = rules.get('default')

        if value is None or value == '':
            if is_required:
                errors.append(f"Missing required field: '{col}'")
            elif default_value is not None:
                cleaned_data[col] = default_value
            else:
                cleaned_data[col] = None # Explicitly set to None if not required and not present
            continue

        # Type conversion and validation
        try:
            if expected_type == str:
                cleaned_value = str(value).strip()
                if max_len and len(cleaned_value) > max_len:
                    errors.append(f"Field '{col}' exceeds max length of {max_len}")
                cleaned_data[col] = cleaned_value
            elif expected_type == bool:
                cleaned_data[col] = str(value).lower() in ('true', '1', 'yes')
            elif expected_type == datetime:
                # Attempt to parse various date formats
                if isinstance(value, datetime):
                    cleaned_data[col] = value.astimezone(timezone.utc) if value.tzinfo is None else value
                else:
                    try:
                        cleaned_data[col] = datetime.fromisoformat(value).astimezone(timezone.utc)
                    except ValueError:
                        try:
                            # Try common format like 'YYYY-MM-DD HH:MM:SS'
                            cleaned_data[col] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S').astimezone(timezone.utc)
                        except ValueError:
                            errors.append(f"Invalid date format for '{col}': '{value}'")
            elif expected_type == dict:
                if isinstance(value, str):
                    try:
                        cleaned_data[col] = json.loads(value)
                    except json.JSONDecodeError:
                        errors.append(f"Invalid JSON format for '{col}': '{value}'")
                elif isinstance(value, dict):
                    cleaned_data[col] = value
                else:
                    errors.append(f"Unexpected type for '{col}': expected dict or JSON string")
            else:
                cleaned_data[col] = value # Fallback for other types, or if type not specified
        except Exception as e:
            errors.append(f"Error processing field '{col}' with value '{value}': {e}")

    if not errors:
        return True, cleaned_data, []
    else:
        return False, {}, errors

def process_offermart_record(session, record: dict) -> tuple[bool, str]:
    """
    Processes a single validated Offermart record, ingesting customer and offer data.
    Returns (success_status, message).
    """
    try:
        # --- 1. Process Customer Data ---
        customer_data = {
            'mobile_number': record.get('mobile_number'),
            'pan_number': record.get('pan_number'),
            'aadhaar_number': record.get('aadhaar_number'),
            'ucid_number': record.get('ucid_number'),
            'customer_360_id': record.get('customer_360_id'),
            'is_dnd': record.get('is_dnd', False),
            'segment': record.get('segment'),
            'attributes': record.get('attributes')
        }

        # Attempt to find existing customer by unique identifiers
        existing_customer = None
        for key in ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number']:
            if customer_data.get(key):
                query_filter = {key: customer_data[key]}
                existing_customer = session.query(Customer).filter_by(**query_filter).first()
                if existing_customer:
                    break

        if existing_customer:
            customer = existing_customer
            # Update existing customer's non-unique attributes if provided
            for key, value in customer_data.items():
                if value is not None and key not in ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number']:
                    setattr(customer, key, value)
            logger.debug(f"Found existing customer: {customer.customer_id}")
        else:
            # Create new customer
            customer = Customer(**{k: v for k, v in customer_data.items() if v is not None})
            session.add(customer)
            session.flush() # Flush to get customer_id for offer
            logger.debug(f"Created new customer: {customer.customer_id}")

        # --- 2. Process Offer Data ---
        # Check for existing offer from the same source_offer_id for this customer
        existing_offer = session.query(Offer).filter_by(
            customer_id=customer.customer_id,
            source_offer_id=record['source_offer_id'],
            source_system=record.get('source_system', 'Offermart')
        ).first()

        offer_data = {
            'customer_id': customer.customer_id,
            'source_offer_id': record['source_offer_id'],
            'offer_type': record['offer_type'],
            'offer_status': record['offer_status'],
            'propensity': record.get('propensity'),
            'loan_application_number': record.get('loan_application_number'),
            'valid_until': record['valid_until'],
            'source_system': record.get('source_system', 'Offermart'),
            'channel': record.get('channel'),
            'is_duplicate': False # Initial state, full deduplication service will update this
        }

        if existing_offer:
            # Update existing offer (FR7: update old offers with new real-time data)
            for key, value in offer_data.items():
                if value is not None:
                    setattr(existing_offer, key, value)
            offer = existing_offer
            logger.debug(f"Updated existing offer: {offer.offer_id}")
        else:
            # Create new offer
            offer = Offer(**{k: v for k, v in offer_data.items() if v is not None})
            session.add(offer)
            logger.debug(f"Created new offer: {offer.offer_id}")

        return True, "Record processed successfully."

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error for record (mobile: {record.get('mobile_number')}, offer_id: {record.get('source_offer_id')}): {e}")
        return False, f"Database integrity error: {e.orig}"
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error processing record (mobile: {record.get('mobile_number')}, offer_id: {record.get('source_offer_id')}): {e}", exc_info=True)
        return False, f"Unexpected error: {e}"

def run_daily_ingestion():
    """
    Main function to run the daily Offermart data ingestion process.
    Reads from a staging file, validates, and ingests data into the CDP.
    """
    logger.info("Starting daily Offermart data ingestion.")
    create_tables_if_not_exist()

    processed_count = 0
    success_count = 0
    error_count = 0
    error_records = [] # To store records that failed validation or ingestion

    # Simulate reading from a CSV staging file
    # In a real scenario, this might involve connecting to another database,
    # an SFTP server, or an API endpoint.
    try:
        if not os.path.exists(OFFERMART_STAGING_FILE):
            logger.error(f"Offermart staging file not found: {OFFERMART_STAGING_FILE}")
            logger.info("Generating mock data for demonstration...")
            generate_mock_offermart_data(OFFERMART_STAGING_FILE)
            logger.info("Mock data generated. Proceeding with ingestion.")

        with open(OFFERMART_STAGING_FILE, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                processed_count += 1
                row_num = i + 2 # +1 for 0-index, +1 for header row

                logger.info(f"Processing row {row_num}: {row.get('mobile_number', 'N/A')}")

                is_valid, cleaned_data, validation_errors = validate_offermart_row(row, row_num)

                if not is_valid:
                    logger.warning(f"Validation failed for row {row_num}: {validation_errors}")
                    error_count += 1
                    error_records.append({'row_number': row_num, 'data': row, 'errors': validation_errors, 'stage': 'validation'})
                    continue

                session = get_db_session()
                try:
                    success, message = process_offermart_record(session, cleaned_data)
                    if success:
                        session.commit()
                        success_count += 1
                        logger.info(f"Successfully ingested record from row {row_num}.")
                    else:
                        session.rollback()
                        error_count += 1
                        error_records.append({'row_number': row_num, 'data': row, 'errors': [message], 'stage': 'ingestion'})
                        logger.error(f"Failed to ingest record from row {row_num}: {message}")
                except Exception as e:
                    session.rollback()
                    error_count += 1
                    error_records.append({'row_number': row_num, 'data': row, 'errors': [str(e)], 'stage': 'unhandled_exception'})
                    logger.critical(f"Unhandled exception during processing row {row_num}: {e}", exc_info=True)
                finally:
                    session.close()

    except FileNotFoundError:
        logger.error(f"Error: Staging file '{OFFERMART_STAGING_FILE}' not found.")
        return
    except Exception as e:
        logger.critical(f"An unexpected error occurred during file processing: {e}", exc_info=True)
        return

    logger.info(f"Daily Offermart ingestion complete.")
    logger.info(f"Total records processed: {processed_count}")
    logger.info(f"Successfully ingested: {success_count}")
    logger.info(f"Failed records: {error_count}")

    if error_records:
        error_file_path = 'data/offermart_ingestion_errors.json'
        with open(error_file_path, 'w', encoding='utf-8') as f:
            json.dump(error_records, f, indent=4)
        logger.warning(f"Details of failed records saved to {error_file_path}")
    else:
        logger.info("No errors found during ingestion.")

def generate_mock_offermart_data(file_path):
    """Generates a mock CSV file for Offermart daily data."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    data = [
        {
            'mobile_number': '9876543210', 'pan_number': 'ABCDE1234F', 'aadhaar_number': '123456789012',
            'ucid_number': 'UCID001', 'customer_360_id': 'C360_001', 'is_dnd': 'false', 'segment': 'C1',
            'source_offer_id': 'OFFER001', 'offer_type': 'Fresh', 'offer_status': 'Active', 'propensity': 'High',
            'loan_application_number': 'LAN001', 'valid_until': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            'source_system': 'Offermart', 'channel': 'SMS', 'attributes': '{"city": "Mumbai", "income": 50000}'
        },
        {
            'mobile_number': '9876543211', 'pan_number': 'FGHIJ5678K', 'aadhaar_number': '234567890123',
            'ucid_number': 'UCID002', 'customer_360_id': 'C360_002', 'is_dnd': 'true', 'segment': 'C2',
            'source_offer_id': 'OFFER002', 'offer_type': 'Preapproved', 'offer_status': 'Active', 'propensity': 'Medium',
            'loan_application_number': 'LAN002', 'valid_until': (datetime.now(timezone.utc) + timedelta(days=45)).isoformat(),
            'source_system': 'Offermart', 'channel': 'Email', 'attributes': '{"city": "Delhi", "occupation": "Engineer"}'
        },
        {
            'mobile_number': '9876543210', 'pan_number': 'ABCDE1234F', # Same customer as OFFER001
            'ucid_number': 'UCID001', 'customer_360_id': 'C360_001', 'is_dnd': 'false', 'segment': 'C1',
            'source_offer_id': 'OFFER003', 'offer_type': 'Enrich', 'offer_status': 'Active', 'propensity': 'Very High',
            'loan_application_number': None, 'valid_until': (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
            'source_system': 'Offermart', 'channel': 'App', 'attributes': '{"city": "Mumbai", "income": 55000}'
        },
        {
            'mobile_number': '9876543212', 'pan_number': 'LMNOP9012Q', 'aadhaar_number': '345678901234',
            'ucid_number': 'UCID003', 'customer_360_id': 'C360_003', 'is_dnd': 'false', 'segment': 'C3',
            'source_offer_id': 'OFFER004', 'offer_type': 'Fresh', 'offer_status': 'Active', 'propensity': 'Low',
            'loan_application_number': 'LAN003', 'valid_until': '2023-01-01 00:00:00', # Expired offer for testing
            'source_system': 'Offermart', 'channel': 'Branch', 'attributes': '{}'
        },
        {
            'mobile_number': '9876543213', 'pan_number': 'RSTUV3456W', 'aadhaar_number': '456789012345',
            'ucid_number': 'UCID004', 'customer_360_id': 'C360_004', 'is_dnd': 'false', 'segment': 'C4',
            'source_offer_id': 'OFFER005', 'offer_type': 'Fresh', 'offer_status': 'Active', 'propensity': 'Medium',
            'loan_application_number': None, 'valid_until': (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            'source_system': 'Offermart', 'channel': 'SMS', 'attributes': '{"marital_status": "Single"}'
        },
        # Invalid record for testing validation
        {
            'mobile_number': '', 'pan_number': 'XYZAB7890C', 'aadhaar_number': '567890123456',
            'ucid_number': 'UCID005', 'customer_360_id': 'C360_005', 'is_dnd': 'false', 'segment': 'C5',
            'source_offer_id': 'OFFER006', 'offer_type': 'Fresh', 'offer_status': 'Active', 'propensity': 'Medium',
            'loan_application_number': None, 'valid_until': (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
            'source_system': 'Offermart', 'channel': 'SMS', 'attributes': '{}'
        },
        {
            'mobile_number': '9999999999', 'pan_number': 'ABCDE1234F', # Duplicate PAN, should link to existing customer
            'ucid_number': 'UCID006', 'customer_360_id': 'C360_006', 'is_dnd': 'false', 'segment': 'C1',
            'source_offer_id': 'OFFER007', 'offer_type': 'Fresh', 'offer_status': 'Active', 'propensity': 'High',
            'loan_application_number': None, 'valid_until': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            'source_system': 'Offermart', 'channel': 'SMS', 'attributes': '{}'
        },
        {
            'mobile_number': '9876543210', 'pan_number': 'ABCDE1234F', # Same customer as OFFER001, updating OFFER001
            'ucid_number': 'UCID001', 'customer_360_id': 'C360_001', 'is_dnd': 'false', 'segment': 'C1',
            'source_offer_id': 'OFFER001', 'offer_type': 'Fresh', 'offer_status': 'Inactive', 'propensity': 'Low', # Status change
            'loan_application_number': 'LAN001', 'valid_until': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            'source_system': 'Offermart', 'channel': 'SMS', 'attributes': '{"city": "Mumbai", "income": 50000}'
        },
    ]

    fieldnames = list(data[0].keys())
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"Mock Offermart data generated at {file_path}")

from datetime import timedelta # Import timedelta for mock data generation

if __name__ == "__main__":
    # Ensure the data directory exists
    os.makedirs('data', exist_ok=True)
    run_daily_ingestion()