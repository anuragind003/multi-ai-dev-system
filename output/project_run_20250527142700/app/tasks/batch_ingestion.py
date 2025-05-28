import logging
from datetime import datetime, timedelta
from uuid import uuid4
import json

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

# Attempt to import Flask app context and database extensions
# This is a common pattern for scripts that might run standalone or within Flask
try:
    from flask import current_app
    from app.extensions import db
    from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign
    # Assuming data_cleanup is a separate module for retention policies
    from app.tasks.data_cleanup import cleanup_old_data as enforce_data_retention
except ImportError:
    # Define mock objects for local testing without a full Flask app
    logging.warning(
        "Could not import Flask app context, app.extensions or app.models. "
        "Using mock objects for standalone execution."
    )

    class MockDB:
        def __init__(self):
            self.session = self
        def add(self, obj): pass
        def commit(self): pass
        def rollback(self): pass
        def query(self, model): return MockQuery(model)
        def delete(self, obj): pass
        def flush(self): pass # Added for getting ID on new objects

    class MockQuery:
        def __init__(self, model):
            self.model = model
            self._filter_args = []
            self._filter_kwargs = {}
            self._order_by_args = []
            self._limit_val = None

        def filter(self, *args):
            self._filter_args.extend(args)
            return self

        def filter_by(self, **kwargs):
            self._filter_kwargs.update(kwargs)
            return self

        def first(self):
            # In a real mock, you'd simulate finding an object.
            # For simplicity, always return None unless specific mock data is set up.
            return None

        def all(self):
            return []

        def get(self, id):
            return None

        def update(self, values):
            pass

        def delete(self):
            pass

    class MockCustomer:
        def __init__(self, **kwargs):
            self.customer_id = kwargs.get('customer_id', uuid4())
            self.mobile_number = kwargs.get('mobile_number')
            self.pan = kwargs.get('pan')
            self.aadhaar_ref_number = kwargs.get('aadhaar_ref_number')
            self.ucid = kwargs.get('ucid')
            self.previous_loan_app_number = kwargs.get('previous_loan_app_number')
            self.customer_attributes = kwargs.get('customer_attributes', {})
            self.customer_segment = kwargs.get('customer_segment')
            self.is_dnd = kwargs.get('is_dnd', False)
            self.created_at = kwargs.get('created_at', datetime.now())
            self.updated_at = kwargs.get('updated_at', datetime.now())

    class MockOffer:
        def __init__(self, **kwargs):
            self.offer_id = kwargs.get('offer_id', uuid4())
            self.customer_id = kwargs.get('customer_id')
            self.offer_type = kwargs.get('offer_type')
            self.offer_status = kwargs.get('offer_status')
            self.propensity_flag = kwargs.get('propensity_flag')
            self.offer_start_date = kwargs.get('offer_start_date')
            self.offer_end_date = kwargs.get('offer_end_date')
            self.loan_application_number = kwargs.get('loan_application_number')
            self.attribution_channel = kwargs.get('attribution_channel')
            self.created_at = kwargs.get('created_at', datetime.now())
            self.updated_at = kwargs.get('updated_at', datetime.now())

    class MockCustomerEvent:
        def __init__(self, **kwargs):
            self.event_id = kwargs.get('event_id', uuid4())
            self.customer_id = kwargs.get('customer_id')
            self.event_type = kwargs.get('event_type')
            self.event_source = kwargs.get('event_source')
            self.event_timestamp = kwargs.get('event_timestamp', datetime.now())
            self.event_details = kwargs.get('event_details', {})

    class MockCampaign:
        def __init__(self, **kwargs):
            self.campaign_id = kwargs.get('campaign_id', uuid4())
            self.campaign_unique_identifier = kwargs.get('campaign_unique_identifier')
            self.campaign_name = kwargs.get('campaign_name')
            self.campaign_date = kwargs.get('campaign_date')
            self.targeted_customers_count = kwargs.get('targeted_customers_count')
            self.attempted_count = kwargs.get('attempted_count')
            self.successfully_sent_count = kwargs.get('successfully_sent_count')
            self.failed_count = kwargs.get('failed_count')
            self.success_rate = kwargs.get('success_rate')
            self.conversion_rate = kwargs.get('conversion_rate')
            self.created_at = kwargs.get('created_at', datetime.now())
            self.updated_at = kwargs.get('updated_at', datetime.now())

    class MockDataIngestionLog:
        def __init__(self, **kwargs):
            self.log_id = kwargs.get('log_id', uuid4())
            self.file_name = kwargs.get('file_name')
            self.upload_timestamp = kwargs.get('upload_timestamp', datetime.now())
            self.status = kwargs.get('status')
            self.error_details = kwargs.get('error_details')
            self.uploaded_by = kwargs.get('uploaded_by')

    db = MockDB()
    Customer = MockCustomer
    Offer = MockOffer
    CustomerEvent = MockCustomerEvent
    DataIngestionLog = MockDataIngestionLog
    Campaign = MockCampaign
    # Mock enforce_data_retention for standalone mode
    def enforce_data_retention():
        _get_logger().info("Mock data retention policy enforced.")

# --- Helper Functions ---

def _get_logger():
    """Helper to get logger, works both in and out of Flask app context."""
    try:
        return current_app.logger
    except RuntimeError:
        return logging.getLogger(__name__)

def _parse_date(date_str):
    """Safely parse date string (YYYY-MM-DD)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        _get_logger().warning(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD. Returning None.")
        return None

def validate_offermart_record(record):
    """
    FR1: Performs basic column-level validation for Offermart data.
    Checks for required fields and basic format.
    Returns (is_valid, error_message).
    """
    required_fields = ['mobile_number', 'offer_type', 'offer_status',
                       'offer_start_date', 'offer_end_date']
    for field in required_fields:
        if not record.get(field):
            return False, f"Missing required field: '{field}'"

    # Basic type/format validation
    mobile_number = record.get('mobile_number')
    if not isinstance(mobile_number, str) or not mobile_number.isdigit():
        return False, "Invalid 'mobile_number' format (must be digits string)."

    if not _parse_date(record['offer_start_date']):
        return False, "Invalid 'offer_start_date' format (YYYY-MM-DD required)."
    if not _parse_date(record['offer_end_date']):
        return False, "Invalid 'offer_end_date' format (YYYY-MM-DD required)."

    # Validate JSONB fields if present
    customer_attributes = record.get('customer_attributes')
    if customer_attributes is not None and not isinstance(customer_attributes, dict):
        return False, "'customer_attributes' must be a dictionary."

    return True, None

def find_or_create_customer(record):
    """
    FR2: Provides a single profile view of the customer based on mobile number,
         PAN, Aadhaar, UCID, or previous loan application number.
    FR14, FR19: Maintains different customer attributes and customer segments.
    """
    logger = _get_logger()
    customer = None
    identifiers = {
        'mobile_number': record.get('mobile_number'),
        'pan': record.get('pan'),
        'aadhaar_ref_number': record.get('aadhaar_ref_number'),
        'ucid': record.get('ucid'),
        'previous_loan_app_number': record.get('previous_loan_app_number')
    }

    # Remove None values from identifiers for query
    valid_identifiers = {k: v for k, v in identifiers.items() if v}

    if not valid_identifiers:
        return None, "No valid identifiers provided for customer."

    # Try to find existing customer using any of the provided identifiers
    query_filters = []
    for key, value in valid_identifiers.items():
        # Use getattr to dynamically access model attributes
        query_filters.append(getattr(Customer, key) == value)

    if query_filters:
        customer = db.session.query(Customer).filter(or_(*query_filters)).first()

    if customer:
        logger.debug(f"Found existing customer: {customer.customer_id}")
        # Update existing customer attributes if new data is available
        # Merge JSONB fields
        if record.get('customer_attributes'):
            customer.customer_attributes = {
                **customer.customer_attributes,
                **record['customer_attributes']
            }
        if record.get('customer_segment'):
            customer.customer_segment = record['customer_segment']
        if 'is_dnd' in record: # Allow updating DND status
            customer.is_dnd = record['is_dnd']
        customer.updated_at = datetime.now()
    else:
        logger.debug(f"Creating new customer with mobile: {record.get('mobile_number')}")
        customer = Customer(
            mobile_number=record.get('mobile_number'),
            pan=record.get('pan'),
            aadhaar_ref_number=record.get('aadhaar_ref_number'),
            ucid=record.get('ucid'),
            previous_loan_app_number=record.get('previous_loan_app_number'),
            customer_attributes=record.get('customer_attributes', {}),
            customer_segment=record.get('customer_segment'),
            is_dnd=record.get('is_dnd', False)
        )
        db.session.add(customer)
        db.session.flush() # To get customer_id for offers before commit

    return customer, None

def process_offer_data(customer_id, offer_record):
    """
    Processes offer data for a given customer.
    FR6: Update old offers in Analytics Offermart with new data received from LTFS CDP
         (Interpreted as: update offers in CDP if new data for same customer/offer comes from Offermart)
    FR15: Maintain flags for Offer statuses: Active, Inactive, and Expired.
    FR16: Maintain flags for Offer types.
    FR20: Apply attribution logic.
    """
    logger = _get_logger()

    # Determine if this is an update to an existing offer or a new offer.
    # This typically requires a unique identifier for the offer from the source system.
    # Assuming 'source_offer_id' might be present in the record.
    source_offer_id = offer_record.get('source_offer_id')

    offer = None
    if source_offer_id:
        # Try to find by a unique source ID if available and mapped to CDP's offer_id
        # Or, if Offermart has its own unique ID, store it in CDP and query by that.
        # For now, let's assume offer_id in CDP is the primary key and not directly
        # mapped to an external source_offer_id unless explicitly designed.
        # A more robust approach would be to have a `source_offer_id` column in `offers` table.
        # For this example, we'll try to find by customer_id and offer_type.
        offer = db.session.query(Offer).filter_by(
            customer_id=customer_id,
            offer_type=offer_record.get('offer_type')
        ).first()
    else:
        # If no source_offer_id, try to find by customer_id and offer_type
        offer = db.session.query(Offer).filter_by(
            customer_id=customer_id,
            offer_type=offer_record.get('offer_type')
        ).first()

    if offer:
        logger.debug(f"Updating existing offer {offer.offer_id} for customer {customer_id}")
        # Update offer details
        offer.offer_status = offer_record.get('offer_status', offer.offer_status)
        offer.offer_type = offer_record.get('offer_type', offer.offer_type)
        offer.propensity_flag = offer_record.get('propensity_flag', offer.propensity_flag)
        offer.offer_start_date = _parse_date(offer_record.get('offer_start_date')) or offer.offer_start_date
        offer.offer_end_date = _parse_date(offer_record.get('offer_end_date')) or offer.offer_end_date
        offer.loan_application_number = offer_record.get('loan_application_number', offer.loan_application_number)
        offer.attribution_channel = offer_record.get('attribution_channel', offer.attribution_channel)
        offer.updated_at = datetime.now()
    else:
        logger.debug(f"Creating new offer for customer {customer_id}")
        offer = Offer(
            customer_id=customer_id,
            offer_type=offer_record.get('offer_type'),
            offer_status=offer_record.get('offer_status'),
            propensity_flag=offer_record.get('propensity_flag'),
            offer_start_date=_parse_date(offer_record.get('offer_start_date')),
            offer_end_date=_parse_date(offer_record.get('offer_end_date')),
            loan_application_number=offer_record.get('loan_application_number'),
            attribution_channel=offer_record.get('attribution_channel', 'Offermart')
        )
        db.session.add(offer)

    # Apply attribution logic (FR20)
    # This is a complex business rule. It would typically involve comparing
    # multiple offers for a customer and setting a 'prevailing' flag or
    # updating the 'attribution_channel' based on predefined rules.
    # For simplicity, if a new offer comes in, its attribution channel is set.
    # A more robust attribution would be a separate service call after all offers
    # for a customer are processed or after the entire batch.
    # Example: `app.services.offer_service.apply_attribution_logic(customer_id)`

    return offer

def deduplicate_customers_and_offers():
    """
    FR3: Deduplication within all Consumer Loan products.
    FR4: Deduplication against the live book (Customer 360).
    FR5: Dedupe Top-up loan offers only within other Top-up offers.

    This is a complex process that would involve:
    1. Identifying duplicate customer records based on mobile, PAN, Aadhaar, UCID.
    2. Merging customer records (e.g., keeping the oldest, or the one with most complete data).
    3. Re-assigning offers and events from merged (duplicate) customers to the canonical customer.
    4. Deleting duplicate customer records.
    5. Specific logic for Top-up offers.
    6. Deduplication against Customer 360 (live book) - this implies an external system call or data sync.

    For this file, we'll provide a high-level placeholder.
    A dedicated service module (e.g., `app.services.deduplication_service`)
    would contain the actual logic.
    """
    logger = _get_logger()
    logger.info("Starting customer and offer deduplication process...")

    # Placeholder for actual deduplication logic.
    # This would involve querying for potential duplicates, applying rules,
    # merging data, and updating foreign keys.
    # Example:
    # from app.services.deduplication_service import perform_deduplication
    # perform_deduplication(db.session) # Pass session for transactional control

    # Simulate some deduplication for logging purposes
    # In a real scenario, this would involve actual DB queries and updates.
    simulated_deduplicated_count = 0
    try:
        # Example of a very simplified deduplication check (not actual logic)
        # This would be replaced by a robust service.
        # For instance, if a mock customer was found and updated, that's a form of deduplication.
        # The `find_or_create_customer` already handles finding existing customers.
        # The `deduplicate_customers_and_offers` would handle merging *distinct* customer records
        # that represent the same person but were created separately due to data inconsistencies.
        logger.info(f"Deduplication process completed. (Simulated {simulated_deduplicated_count} merges)")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error during deduplication: {e}")
        raise # Re-raise to indicate failure in the pipeline

# --- Main Batch Ingestion Function ---

def run_daily_batch_processes():
    """
    Main function to run daily batch processes for data ingestion from Offermart.
    FR7: Receive Offer data and Customer data from Offermart daily by creating a
         staging area (Offer DB to CDP DB).
    NFR5: Handle daily data pushes from Offermart to CDP.
    """
    logger = _get_logger()
    log_id = uuid4()
    # Simulate a file name for logging purposes
    file_name = f"offermart_daily_ingestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    logger.info(f"--- Starting daily batch ingestion pipeline for {file_name} ---")

    total_records = 0
    successful_records = 0
    failed_records_details = [] # List of dicts: {'record': ..., 'errors': [...]}
    ingestion_status = 'SUCCESS'

    try:
        # Simulate fetching data from Offermart. In a real scenario, this would
        # involve reading from a shared directory, SFTP, or a direct DB link.
        offermart_data = _simulate_offermart_data()
        total_records = len(offermart_data)

        for i, record in enumerate(offermart_data):
            record_errors = []
            try:
                is_valid, validation_error = validate_offermart_record(record)
                if not is_valid:
                    record_errors.append(f"Validation failed: {validation_error}")
                    raise ValueError(validation_error)

                customer, customer_error = find_or_create_customer(record)
                if customer_error:
                    record_errors.append(f"Customer processing failed: {customer_error}")
                    raise ValueError(customer_error)

                process_offer_data(customer.customer_id, record)

                db.session.commit()
                successful_records += 1
            except (ValueError, SQLAlchemyError) as e:
                db.session.rollback()
                error_msg = f"Record {i+1} failed: {e}. Data: {record}"
                logger.error(error_msg)
                record_errors.append(str(e))
                failed_records_details.append({'record': record, 'errors': record_errors})
                ingestion_status = 'PARTIAL' if successful_records > 0 else 'FAILED'
            except Exception as e:
                db.session.rollback()
                error_msg = f"Unexpected error processing record {i+1}: {e}. Data: {record}"
                logger.critical(error_msg)
                record_errors.append(f"Unexpected error: {e}")
                failed_records_details.append({'record': record, 'errors': record_errors})
                ingestion_status = 'PARTIAL' if successful_records > 0 else 'FAILED'

        logger.info(f"Processed {total_records} records. "
                    f"Successful: {successful_records}, Failed: {len(failed_records_details)}")

        # Log the ingestion result to DataIngestionLog (FR31, FR32)
        log_entry = DataIngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status=ingestion_status,
            error_details=json.dumps(failed_records_details) if failed_records_details else None,
            uploaded_by="System (Offermart Batch)"
        )
        db.session.add(log_entry)
        db.session.commit()
        logger.info(f"Ingestion log recorded with status: {ingestion_status}")

        # Step 2: Perform deduplication after all data is ingested
        # This should ideally be a separate, idempotent process that can be run
        # independently or as part of the daily pipeline.
        deduplicate_customers_and_offers()

        # Step 3: Enforce data retention policies (NFR3, NFR4)
        enforce_data_retention()

    except Exception as e:
        db.session.rollback()
        logger.critical(f"Fatal error during batch ingestion pipeline: {e}")
        # Ensure a log entry is made even for fatal pipeline errors
        log_entry = DataIngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status='FAILED',
            error_details=f"Fatal pipeline error: {e}",
            uploaded_by="System (Offermart Batch)"
        )
        db.session.add(log_entry)
        db.session.commit()
        ingestion_status = 'FAILED'

    logger.info(f"--- Daily batch ingestion pipeline completed with overall status: {ingestion_status} ---")


def _simulate_offermart_data():
    """
    Simulates fetching daily Offermart data.
    In a real application, this would read from a file, an external database, etc.
    """
    return [
        {
            'mobile_number': '9876543210',
            'pan': 'ABCDE1234F',
            'aadhaar_ref_number': '123456789012',
            'ucid': 'UCID001',
            'previous_loan_app_number': 'LAN001',
            'customer_attributes': {'income': 50000, 'city': 'Mumbai'},
            'customer_segment': 'C1',
            'offer_type': 'Preapproved',
            'offer_status': 'Active',
            'propensity_flag': 'high_credit_score',
            'offer_start_date': '2023-10-01',
            'offer_end_date': '2023-11-30',
            'loan_application_number': None,
            'attribution_channel': 'Offermart',
            'is_dnd': False
        },
        {
            'mobile_number': '9876543211',
            'pan': 'FGHIJ5678K',
            'aadhaar_ref_number': '234567890123',
            'ucid': 'UCID002',
            'customer_attributes': {'income': 75000, 'city': 'Delhi'},
            'customer_segment': 'C2',
            'offer_type': 'Loyalty',
            'offer_status': 'Active',
            'propensity_flag': 'existing_customer',
            'offer_start_date': '2023-10-15',
            'offer_end_date': '2023-12-31',
            'loan_application_number': None,
            'attribution_channel': 'Offermart',
            'is_dnd': False
        },
        {
            'mobile_number': '9876543210', # Duplicate mobile number for testing deduplication
            'pan': 'ABCDE1234F', # Same PAN
            'aadhaar_ref_number': '123456789012', # Same Aadhaar
            'ucid': 'UCID001', # Same UCID
            'customer_attributes': {'income': 55000, 'city': 'Mumbai', 'occupation': 'Engineer'}, # Enriched attributes
            'customer_segment': 'C1',
            'offer_type': 'Topup', # New offer type for existing customer
            'offer_status': 'Active',
            'propensity_flag': 'good_payment_history',
            'offer_start_date': '2023-11-01',
            'offer_end_date': '2024-01-31',
            'loan_application_number': None,
            'attribution_channel': 'Offermart',
            'is_dnd': False
        },
        {
            'mobile_number': '9999999999',
            'pan': 'LMNOP9012Q',
            'offer_type': 'E-aggregator',
            'offer_status': 'Active',
            'offer_start_date': '2023-11-05',
            'offer_end_date': '2023-12-05',
            'is_dnd': True # DND customer
        },
        {
            'mobile_number': '1111111111', # Missing required fields for validation test
            'offer_type': 'Prospect',
            'offer_status': 'Active',
            'offer_start_date': '2023-11-01',
            # 'offer_end_date': '2023-12-01' # Missing offer_end_date
        },
        {
            'mobile_number': '2222222222',
            'pan': 'RSTUV3456W',
            'offer_type': 'Prospect',
            'offer_status': 'Active',
            'offer_start_date': '2023-11-01',
            'offer_end_date': '2023-12-01',
            'customer_attributes': 'not_a_json' # Invalid attribute type
        }
    ]

if __name__ == '__main__':
    # This block is for local testing/demonstration.
    # In a real Flask application, you would typically run this via a Flask CLI command
    # or a Celery worker, ensuring the Flask app context and database are properly initialized.
    print("Running batch processes (this might require a Flask app context and DB setup).")
    print("If you see 'WARNING: Could not import Flask app context, app.extensions or app.models. "
          "Using mock objects for standalone execution.',")
    print("this script is running in standalone mode with mocked DB interactions.")
    print("For full functionality, run within a Flask application context.")

    # Configure basic logging for standalone execution
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Call the main function directly for standalone mock testing
    run_daily_batch_processes()