import logging
import uuid
from datetime import datetime, date
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, String, Boolean, Date, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import PrimaryKeyConstraint
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Any
import json # For parsing JSONB data from pandas DataFrame

# --- Configuration (assuming settings are loaded from .env) ---
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@host:5432/cdp_db" # Default for local testing
    OFFERMART_DATA_PATH: str = "data/offermart_data.csv" # Placeholder for daily data source

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# --- Database Setup (simplified for job, typically in app.db) ---
# This part would ideally be imported from app.db.base and app.db.session
# For a standalone job file, we define it here for completeness.
Base = declarative_base()
engine = create_engine(settings.DATABASE_URL)

# --- Database Models (simplified, assuming these are defined in app.models.models) ---
# Re-defining them here for self-containment of the job script,
# but in a real project, these would be imported.
class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(20), unique=True, nullable=True)
    pan_number = Column(String(10), unique=True, nullable=True)
    aadhaar_ref_number = Column(String(12), unique=True, nullable=True)
    ucid_number = Column(String(50), unique=True, nullable=True)
    previous_loan_app_number = Column(String(50), unique=True, nullable=True)
    customer_attributes = Column(JSONB, default={})
    customer_segments = Column(Text, default="[]") # Storing as TEXT for simplicity, convert to list
    propensity_flag = Column(String(50), nullable=True)
    dnd_status = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        PrimaryKeyConstraint('customer_id', name='pk_customers'),
    )

class Offer(Base):
    __tablename__ = "offers"
    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False) # No ForeignKey for simplicity in job, but should be in real app
    offer_type = Column(String(50))
    offer_status = Column(String(50)) # e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'
    product_type = Column(String(50))
    offer_details = Column(JSONB, default={})
    offer_start_date = Column(Date)
    offer_end_date = Column(Date)
    is_journey_started = Column(Boolean, default=False)
    loan_application_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        PrimaryKeyConstraint('offer_id', name='pk_offers'),
    )

class OfferHistory(Base):
    __tablename__ = "offer_history"
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), nullable=False) # No ForeignKey for simplicity in job
    customer_id = Column(UUID(as_uuid=True), nullable=False) # No ForeignKey for simplicity in job
    change_timestamp = Column(DateTime(timezone=True), default=datetime.now)
    old_offer_status = Column(String(50), nullable=True)
    new_offer_status = Column(String(50), nullable=True)
    change_reason = Column(Text, nullable=True)
    snapshot_offer_details = Column(JSONB, default={})

    __table_args__ = (
        PrimaryKeyConstraint('history_id', name='pk_offer_history'),
    )

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def get_db_session():
    """Yields a SQLAlchemy session."""
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()

def find_customer(db: Session, mobile: Optional[str], pan: Optional[str], aadhaar: Optional[str], ucid: Optional[str], prev_loan_app: Optional[str]):
    """Finds an existing customer by any of the unique identifiers."""
    query = db.query(Customer)
    conditions = []
    if mobile:
        conditions.append(Customer.mobile_number == mobile)
    if pan:
        conditions.append(Customer.pan_number == pan)
    if aadhaar:
        conditions.append(Customer.aadhaar_ref_number == aadhaar)
    if ucid:
        conditions.append(Customer.ucid_number == ucid)
    if prev_loan_app:
        conditions.append(Customer.previous_loan_app_number == prev_loan_app)

    if not conditions:
        return None

    # Combine conditions with OR
    combined_condition = conditions[0]
    for i in range(1, len(conditions)):
        combined_condition |= conditions[i]

    return query.filter(combined_condition).first()

def create_or_update_customer(db: Session, customer_data: Dict[str, Any]):
    """Creates a new customer or updates an existing one."""
    mobile = customer_data.get('mobile_number')
    pan = customer_data.get('pan_number')
    aadhaar = customer_data.get('aadhaar_ref_number')
    ucid = customer_data.get('ucid_number')
    prev_loan_app = customer_data.get('previous_loan_app_number')

    customer = find_customer(db, mobile, pan, aadhaar, ucid, prev_loan_app)

    if customer:
        # Update existing customer attributes
        logger.info(f"Updating existing customer: {customer.customer_id}")
        for key, value in customer_data.items():
            if hasattr(customer, key) and value is not None:
                # Special handling for JSONB and Text fields that might be stringified
                if key == 'customer_attributes' and isinstance(value, str):
                    try:
                        setattr(customer, key, json.loads(value))
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON for customer_attributes: {value}")
                        setattr(customer, key, {}) # Default to empty dict on error
                elif key == 'customer_segments' and isinstance(value, str):
                    try:
                        # Assuming segments are stored as a JSON string of a list
                        setattr(customer, key, json.dumps(json.loads(value)))
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON for customer_segments: {value}")
                        setattr(customer, key, "[]") # Default to empty list string on error
                else:
                    setattr(customer, key, value)
        customer.updated_at = datetime.now()
    else:
        # Create new customer
        logger.info(f"Creating new customer: {customer_data.get('mobile_number')}")
        # Ensure JSONB and Text fields are correctly formatted for new customer
        if isinstance(customer_data.get('customer_attributes'), str):
            try:
                customer_data['customer_attributes'] = json.loads(customer_data['customer_attributes'])
            except json.JSONDecodeError:
                customer_data['customer_attributes'] = {}
        if isinstance(customer_data.get('customer_segments'), str):
            try:
                customer_data['customer_segments'] = json.dumps(json.loads(customer_data['customer_segments']))
            except json.JSONDecodeError:
                customer_data['customer_segments'] = "[]"

        customer = Customer(**customer_data)
        db.add(customer)
    db.flush() # Flush to get customer_id if new
    return customer

def process_offer_precedence(db: Session, customer: Customer, new_offer_data: Dict[str, Any]):
    """
    Applies offer precedence rules (FR25-FR32) and determines the status of the new offer.
    Returns the determined status for the new offer and any old offers to be updated.
    """
    new_offer_product_type = new_offer_data.get('product_type')
    new_offer_is_journey_started = new_offer_data.get('is_journey_started', False)

    # Fetch all active offers for the customer
    existing_offers = db.query(Offer).filter(
        Offer.customer_id == customer.customer_id,
        Offer.offer_status == 'Active'
    ).all()

    # Default status for new offer
    new_offer_status = 'Active'
    old_offers_to_update = []

    # Define a simple hierarchy for offer types based on FR29-FR32
    # Higher value means higher precedence (cannot be replaced by lower precedence offer)
    OFFER_HIERARCHY = {
        'Employee Loan': 5,
        'TW Loyalty': 4,
        'Top-up': 3,
        'Preapproved E-aggregator': 2,
        'Prospect': 1,
        'Insta': 0, # Insta/CLEAG are generally real-time and might override lower precedence
        'E-aggregator': 0, # Insta/CLEAG are generally real-time and might override lower precedence
    }

    for existing_offer in existing_offers:
        existing_product_type = existing_offer.product_type
        existing_is_journey_started = existing_offer.is_journey_started

        # FR15: Prevent modification of customer offers with a started loan application journey.
        if existing_is_journey_started:
            logger.info(f"Customer {customer.customer_id} has an existing offer ({existing_offer.offer_id}) of type '{existing_product_type}' with journey started. New offer '{new_offer_product_type}' will be marked as Duplicate.")
            new_offer_status = 'Duplicate'
            return new_offer_status, old_offers_to_update # New offer is duplicate, existing active offer remains

        existing_precedence = OFFER_HIERARCHY.get(existing_product_type, -1)
        new_precedence = OFFER_HIERARCHY.get(new_offer_product_type, -1)

        if existing_precedence > new_precedence:
            # FR29-FR32: Existing offer has higher precedence, new offer cannot be uploaded.
            logger.info(f"Existing offer type '{existing_product_type}' has higher precedence ({existing_precedence}) than new offer type '{new_offer_product_type}' ({new_precedence}). New offer marked as Duplicate.")
            new_offer_status = 'Duplicate'
            return new_offer_status, old_offers_to_update # New offer is duplicate, existing active offer remains

        elif existing_precedence < new_precedence:
            # New offer has higher precedence, existing offer should be expired/duplicated.
            logger.info(f"New offer type '{new_offer_product_type}' has higher precedence ({new_precedence}) than existing offer type '{existing_product_type}' ({existing_precedence}). Existing offer '{existing_offer.offer_id}' will be marked as Expired.")
            old_offers_to_update.append({
                'offer': existing_offer,
                'new_status': 'Expired',
                'reason': f"Replaced by higher precedence offer type: {new_offer_product_type}"
            })
            new_offer_status = 'Active' # New offer becomes active
            # Continue checking other existing offers, but the new one is likely active.

        else: # existing_precedence == new_precedence
            # Same precedence or unknown precedence.
            # FR20: If an Enrich offer's journey has not started, it shall flow to CDP, and the previous offer will be moved to Duplicate.
            if new_offer_data.get('offer_type') == 'Enrich' and not new_offer_is_journey_started:
                logger.info(f"New offer is 'Enrich' and journey not started. Existing offer '{existing_product_type}' ({existing_offer.offer_id}) will be marked as Duplicate.")
                old_offers_to_update.append({
                    'offer': existing_offer,
                    'new_status': 'Duplicate',
                    'reason': f"Replaced by Enrich offer"
                })
                new_offer_status = 'Active'
            else:
                # General case for same precedence or if no specific rule applies:
                # If a new offer comes for the same product type, and no journey started for existing,
                # the newest offer (the one being ingested) becomes active, old one becomes duplicate.
                logger.info(f"New offer '{new_offer_product_type}' replacing existing offer '{existing_product_type}' ({existing_offer.offer_id}). Existing offer will be marked as Duplicate.")
                old_offers_to_update.append({
                    'offer': existing_offer,
                    'new_status': 'Duplicate',
                    'reason': f"Replaced by new offer of same/similar type"
                })
                new_offer_status = 'Active'

    return new_offer_status, old_offers_to_update

def record_offer_history(db: Session, offer: Offer, old_status: Optional[str], new_status: str, reason: str):
    """Records a change in offer status to offer_history."""
    history_entry = OfferHistory(
        offer_id=offer.offer_id,
        customer_id=offer.customer_id,
        old_offer_status=old_status,
        new_offer_status=new_status,
        change_reason=reason,
        snapshot_offer_details=offer.offer_details # Snapshot current details
    )
    db.add(history_entry)
    logger.info(f"Recorded offer history for offer {offer.offer_id}: {old_status if old_status else 'N/A'} -> {new_status} ({reason})")


def ingest_daily_offermart_data(file_path: str):
    """
    Main function to ingest daily customer and offer data from Offermart.
    """
    logger.info(f"Starting daily Offermart data ingestion from {file_path}")
    success_count = 0
    error_count = 0
    error_records = []

    try:
        # Read data from the specified file path
        df = pd.read_csv(file_path)
        logger.info(f"Successfully loaded {len(df)} records from {file_path}")

        # Basic column-level validation (FR1, NFR3)
        required_customer_identifier_cols = ['mobile_number', 'pan_number', 'aadhaar_ref_number', 'ucid_number', 'previous_loan_app_number']
        required_offer_cols = ['product_type', 'offer_start_date', 'offer_end_date']

        # Convert date columns
        for col in ['offer_start_date', 'offer_end_date']:
            if col in df.columns:
                # Convert to datetime first, then to date, coercing errors
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        with next(get_db_session()) as db:
            for index, row in df.iterrows():
                try:
                    # Prepare customer data
                    customer_data = {
                        'mobile_number': str(int(row['mobile_number'])) if pd.notna(row['mobile_number']) else None,
                        'pan_number': row['pan_number'] if pd.notna(row['pan_number']) else None,
                        'aadhaar_ref_number': str(int(row['aadhaar_ref_number'])) if pd.notna(row['aadhaar_ref_number']) else None,
                        'ucid_number': row['ucid_number'] if pd.notna(row['ucid_number']) else None,
                        'previous_loan_app_number': row['previous_loan_app_number'] if pd.notna(row['previous_loan_app_number']) else None,
                        'customer_attributes': row.get('customer_attributes', '{}'), # Pass as string, will be parsed in create_or_update_customer
                        'customer_segments': row.get('customer_segments', '[]'), # Pass as string, will be parsed in create_or_update_customer
                        'propensity_flag': row.get('propensity_flag'),
                        'dnd_status': bool(row.get('dnd_status', False))
                    }

                    # Basic validation: At least one identifier must be present
                    if not any(customer_data[key] for key in required_customer_identifier_cols):
                        raise ValueError("Customer record missing all primary identifiers.")

                    # Create or update customer
                    customer = create_or_update_customer(db, customer_data)

                    # Prepare offer data
                    offer_data = {
                        'customer_id': customer.customer_id,
                        'offer_type': row.get('offer_type', 'Fresh'), # Default to 'Fresh' if not specified
                        'product_type': row['product_type'],
                        'offer_details': row.get('offer_details', '{}'), # Pass as string, will be parsed below
                        'offer_start_date': row['offer_start_date'],
                        'offer_end_date': row['offer_end_date'],
                        'is_journey_started': bool(row.get('is_journey_started', False)),
                        'loan_application_id': row.get('loan_application_id')
                    }

                    # Validate required offer fields and dates
                    if not all(pd.notna(offer_data[key]) for key in ['product_type', 'offer_start_date', 'offer_end_date']):
                        raise ValueError("Offer record missing required fields (product_type, start/end date) or dates are invalid.")

                    # Parse offer_details JSON string
                    if isinstance(offer_data['offer_details'], str):
                        try:
                            offer_data['offer_details'] = json.loads(offer_data['offer_details'])
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON for offer_details in row {index}: {row.get('offer_details')}")
                            offer_data['offer_details'] = {} # Default to empty dict on error

                    # Apply offer precedence and deduplication logic
                    new_offer_status, old_offers_to_update = process_offer_precedence(db, customer, offer_data)
                    offer_data['offer_status'] = new_offer_status

                    # Update old offers if necessary
                    for old_offer_info in old_offers_to_update:
                        old_offer = old_offer_info['offer']
                        old_status = old_offer.offer_status
                        new_status = old_offer_info['new_status']
                        reason = old_offer_info['reason']

                        if old_status != new_status:
                            old_offer.offer_status = new_status
                            old_offer.updated_at = datetime.now()
                            db.add(old_offer)
                            record_offer_history(db, old_offer, old_status, new_status, reason)

                    # Create or update the new offer
                    if new_offer_status == 'Active':
                        new_offer = Offer(**offer_data)
                        db.add(new_offer)
                        record_offer_history(db, new_offer, None, 'Active', 'New offer ingested')
                        logger.info(f"Added/Activated new offer for customer {customer.customer_id}: {new_offer.product_type}")
                    else:
                        logger.info(f"New offer for customer {customer.customer_id} of type '{new_offer_product_type}' marked as {new_offer_status}. Not added as active.")
                        # If we want to store duplicate offers (even if not active), we would create an Offer object
                        # with the 'Duplicate' status and add it to the DB. For now, we just log and count as error.
                        error_count += 1
                        error_records.append({**row.to_dict(), 'Error Desc': f"Offer marked as {new_offer_status} due to precedence rules."})
                        continue # Skip success count for duplicates/non-active offers

                    db.commit()
                    success_count += 1

                except Exception as e:
                    db.rollback()
                    logger.error(f"Error processing row {index}: {e}", exc_info=True)
                    error_count += 1
                    error_records.append({**row.to_dict(), 'Error Desc': str(e)})

    except FileNotFoundError:
        logger.error(f"Offermart data file not found at {file_path}")
        return {"status": "failed", "message": "File not found"}
    except pd.errors.EmptyDataError:
        logger.warning(f"Offermart data file at {file_path} is empty.")
        return {"status": "completed", "message": "No data to ingest."}
    except Exception as e:
        logger.critical(f"Critical error during ingestion process: {e}", exc_info=True)
        return {"status": "failed", "message": f"Critical ingestion error: {e}"}

    logger.info(f"Daily Offermart data ingestion completed. Success: {success_count}, Errors: {error_count}")

    # Generate error file if any errors occurred (FR46)
    if error_records:
        error_df = pd.DataFrame(error_records)
        error_file_path = f"data/offermart_ingestion_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        error_df.to_csv(error_file_path, index=False)
        logger.warning(f"Error records saved to {error_file_path}")

    return {"status": "completed", "success_count": success_count, "error_count": error_count}

# --- Main execution block (for direct script execution) ---
if __name__ == "__main__":
    # This block is for testing the job directly.
    # In a real FastAPI application, this would be triggered by a scheduler or an API endpoint.

    # Ensure the 'data' directory exists for input/output files
    import os
    os.makedirs('data', exist_ok=True)

    # Create a dummy CSV for testing if it doesn't exist
    dummy_data_path = settings.OFFERMART_DATA_PATH
    if not os.path.exists(dummy_data_path):
        logger.info(f"Creating dummy data file at {dummy_data_path} for testing.")
        dummy_data = {
            'mobile_number': [9876543210, 9876543211, 9876543212, 9876543210, 9876543213, 9876543214, 9876543215],
            'pan_number': ['ABCDE1234A', 'BCDEF2345B', 'CDEFG3456C', 'ABCDE1234A', 'DEFGH4567D', 'HIJKL5678E', 'MNOPQ6789F'],
            'aadhaar_ref_number': [123456789012, 123456789013, 123456789014, 123456789012, 123456789015, 123456789016, 123456789017],
            'ucid_number': ['UCID001', 'UCID002', 'UCID003', 'UCID001', 'UCID004', 'UCID005', 'UCID006'],
            'previous_loan_app_number': ['LAN001', 'LAN002', 'LAN003', 'LAN001', 'LAN004', 'LAN005', 'LAN006'],
            'product_type': ['Preapproved', 'Loyalty', 'Insta', 'E-aggregator', 'Top-up', 'Employee Loan', 'Prospect'],
            'offer_type': ['Fresh', 'Fresh', 'Fresh', 'Enrich', 'Fresh', 'Fresh', 'Fresh'],
            'offer_start_date': ['2023-01-01', '2023-01-05', '2023-01-10', '2023-01-01', '2023-01-15', '2023-01-20', '2023-01-25'],
            'offer_end_date': ['2023-03-31', '2023-04-30', '2023-05-31', '2023-03-31', '2023-06-30', '2023-07-31', '2023-08-31'],
            'offer_details': [
                '{"loan_amount": 100000, "interest_rate": 10.5}',
                '{"loan_amount": 50000, "tenure": 12}',
                '{"loan_amount": 200000, "eligibility_score": 85}',
                '{"loan_amount": 120000, "interest_rate": 9.8}', # Enrich for first customer (Preapproved)
                '{"loan_amount": 75000, "topup_reason": "home_renovation"}',
                '{"loan_amount": 300000, "employee_id": "EMP001"}',
                '{"loan_amount": 25000, "marketing_campaign": "Spring2023"}'
            ],
            'customer_attributes': [
                '{"age": 30, "city": "Mumbai"}',
                '{"age": 45, "city": "Delhi"}',
                '{"age": 25, "city": "Bangalore"}',
                '{"age": 30, "city": "Mumbai"}',
                '{"age": 50, "city": "Chennai"}',
                '{"age": 35, "city": "Pune"}',
                '{"age": 28, "city": "Hyderabad"}'
            ],
            'customer_segments': [
                '["C1", "C5"]',
                '["C2"]',
                '["C3", "C6"]',
                '["C1", "C5"]',
                '["C4"]',
                '["C1", "C7"]',
                '["C8"]'
            ],
            'propensity_flag': ['High', 'Medium', 'High', 'High', 'Medium', 'High', 'Low'],
            'dnd_status': [False, False, True, False, False, False, False], # Customer 3 is DND
            'is_journey_started': [False, False, False, False, False, False, False],
            'loan_application_id': [None, None, None, None, None, None, None]
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv(dummy_data_path, index=False)

    # Create tables in the database if they don't exist
    # This is for local testing setup. In production, use Alembic migrations.
    logger.info("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables checked/created.")

    # Run the ingestion job
    result = ingest_daily_offermart_data(settings.OFFERMART_DATA_PATH)
    logger.info(f"Ingestion Result: {result}")

    # Example of how to query data after ingestion (for verification)
    with next(get_db_session()) as db:
        customers = db.query(Customer).all()
        offers = db.query(Offer).all()
        offer_histories = db.query(OfferHistory).all()

        logger.info("\n--- Current Customers ---")
        for cust in customers:
            logger.info(f"ID: {cust.customer_id}, Mobile: {cust.mobile_number}, PAN: {cust.pan_number}, DND: {cust.dnd_status}, Segments: {cust.customer_segments}")

        logger.info("\n--- Current Offers ---")
        for offer in offers:
            logger.info(f"ID: {offer.offer_id}, Cust ID: {offer.customer_id}, Product: {offer.product_type}, Status: {offer.offer_status}, Journey Started: {offer.is_journey_started}")

        logger.info("\n--- Offer History ---")
        for hist in offer_histories:
            logger.info(f"Offer ID: {hist.offer_id}, Old Status: {hist.old_offer_status}, New Status: {hist.new_offer_status}, Reason: {hist.change_reason}")