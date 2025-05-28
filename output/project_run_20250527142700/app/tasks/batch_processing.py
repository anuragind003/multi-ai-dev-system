import logging
from datetime import datetime, timedelta
from uuid import uuid4
import pandas as pd

from flask import current_app

# Attempt to import Flask app context and database extensions
# This is a common pattern for scripts that might run standalone or within Flask
try:
    from app.extensions import db
    from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog
    from sqlalchemy.exc import SQLAlchemyError, IntegrityError
    from sqlalchemy import or_, and_
except ImportError:
    # Define mock objects for local testing without a full Flask app
    logging.warning("Could not import app.extensions or app.models. Using mock objects.")
    class MockDB:
        def __init__(self):
            self.session = self
        def add(self, obj): pass
        def commit(self): pass
        def rollback(self): pass
        def query(self, model): return MockQuery(model)
        def delete(self, obj): pass
        def bulk_save_objects(self, objs): pass
        def merge(self, obj): return obj # Simulate merge for existing objects
        def close(self): pass # For session closing

    class MockQuery:
        def __init__(self, model): self.model = model
        def filter(self, *args, **kwargs): return self
        def filter_by(self, *args, **kwargs): return self
        def all(self): return []
        def first(self): return None
        def update(self, values, synchronize_session=False): pass
        def delete(self, synchronize_session=False): pass
        def join(self, *args, **kwargs): return self
        def group_by(self, *args, **kwargs): return self
        def having(self, *args, **kwargs): return self
        def count(self): return 0
        def order_by(self, *args, **kwargs): return self

    class MockModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.created_at = kwargs.get('created_at', datetime.now())
            self.updated_at = kwargs.get('updated_at', datetime.now())
            self.__dict__['_sa_instance_state'] = None # Mock SQLAlchemy internal state

    class MockCustomer(MockModel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.customer_id = kwargs.get('customer_id', uuid4())
            self.mobile_number = kwargs.get('mobile_number')
            self.pan = kwargs.get('pan')
            self.aadhaar_ref_number = kwargs.get('aadhaar_ref_number')
            self.ucid = kwargs.get('ucid')
            self.previous_loan_app_number = kwargs.get('previous_loan_app_number')
            self.customer_attributes = kwargs.get('customer_attributes', {})
            self.customer_segment = kwargs.get('customer_segment')
            self.is_dnd = kwargs.get('is_dnd', False)

    class MockOffer(MockModel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.offer_id = kwargs.get('offer_id', uuid4())
            self.customer_id = kwargs.get('customer_id')
            self.offer_type = kwargs.get('offer_type')
            self.offer_status = kwargs.get('offer_status')
            self.propensity_flag = kwargs.get('propensity_flag')
            self.offer_start_date = kwargs.get('offer_start_date')
            self.offer_end_date = kwargs.get('offer_end_date')
            self.loan_application_number = kwargs.get('loan_application_number')
            self.attribution_channel = kwargs.get('attribution_channel')

    class MockCustomerEvent(MockModel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.event_id = kwargs.get('event_id', uuid4())
            self.customer_id = kwargs.get('customer_id')
            self.event_type = kwargs.get('event_type')
            self.event_source = kwargs.get('event_source')
            self.event_timestamp = kwargs.get('event_timestamp', datetime.now())
            self.event_details = kwargs.get('event_details', {})

    class MockCampaign(MockModel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.campaign_id = kwargs.get('campaign_id', uuid4())
            self.campaign_unique_identifier = kwargs.get('campaign_unique_identifier')
            self.campaign_name = kwargs.get('campaign_name')
            self.campaign_date = kwargs.get('campaign_date')
            self.targeted_customers_count = kwargs.get('targeted_customers_count', 0)
            self.attempted_count = kwargs.get('attempted_count', 0)
            self.successfully_sent_count = kwargs.get('successfully_sent_count', 0)
            self.failed_count = kwargs.get('failed_count', 0)
            self.success_rate = kwargs.get('success_rate', 0.0)
            self.conversion_rate = kwargs.get('conversion_rate', 0.0)

    class MockDataIngestionLog(MockModel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
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
    Campaign = MockCampaign
    DataIngestionLog = MockDataIngestionLog
    SQLAlchemyError = Exception
    IntegrityError = Exception
    or_ = lambda *args: True # Mock for logical OR
    and_ = lambda *args: True # Mock for logical AND


# Configure logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def _get_logger():
    """Helper to get logger, works both in and out of Flask app context."""
    try:
        return current_app.logger
    except RuntimeError:
        return logger

def perform_deduplication():
    """
    FR3, FR4, FR5: Performs deduplication within all Consumer Loan products
    and against the live book (Customer 360).
    This is a complex operation that would involve:
    1. Identifying potential duplicates based on mobile, PAN, Aadhaar, UCID, previous_loan_app_number.
    2. Applying specific rules for Top-up loan offers (FR5).
    3. Merging or marking duplicate customer records, ensuring a single profile view (FR2).
    4. Updating associated offers and events to point to the canonical customer ID.
    """
    logger = _get_logger()
    logger.info("Starting deduplication process...")

    try:
        # This is a simplified example. A real deduplication process would involve:
        # - More sophisticated matching across multiple identifiers (mobile, PAN, Aadhaar, UCID, previous_loan_app_number).
        # - Handling of partial matches or fuzzy matching.
        # - Specific rules for 'Top-up loan offers' (FR5).
        # - Logic to determine the 'canonical' customer (e.g., oldest, most complete data).
        # - A robust merging strategy (e.g., transferring attributes, offers, events).

        # Example: Find customers with duplicate mobile numbers (simplified for demonstration)
        # In a production system, this would be a more complex query or a dedicated service.
        duplicate_identifiers = db.session.query(Customer.mobile_number) \
            .group_by(Customer.mobile_number) \
            .having(db.func.count(Customer.customer_id) > 1) \
            .all()

        processed_duplicates_count = 0
        for row in duplicate_identifiers:
            mobile_number = row.mobile_number
            # Get all customers with this mobile number, ordered by creation date to pick canonical
            customers_with_same_id = db.session.query(Customer) \
                .filter_by(mobile_number=mobile_number) \
                .order_by(Customer.created_at.asc()) \
                .all()

            if not customers_with_same_id:
                continue

            canonical_customer = customers_with_same_id[0]
            duplicate_customers = customers_with_same_id[1:]

            for dup_customer in duplicate_customers:
                # Reassign offers from duplicate to canonical customer
                db.session.query(Offer).filter_by(customer_id=dup_customer.customer_id).update(
                    {'customer_id': canonical_customer.customer_id, 'updated_at': datetime.now()}, synchronize_session=False
                )
                # Reassign customer events from duplicate to canonical customer
                db.session.query(CustomerEvent).filter_by(customer_id=dup_customer.customer_id).update(
                    {'customer_id': canonical_customer.customer_id, 'event_timestamp': datetime.now()}, synchronize_session=False
                )
                # Delete the duplicate customer record
                db.session.delete(dup_customer)
                processed_duplicates_count += 1
                logger.info(f"Merged duplicate customer {dup_customer.customer_id} into canonical {canonical_customer.customer_id}")

        db.session.commit()
        logger.info(f"Deduplication completed. Processed {processed_duplicates_count} duplicate customer records.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during deduplication: {e}", exc_info=True)
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during deduplication: {e}", exc_info=True)
        raise

def apply_attribution_logic():
    """
    FR20: Applies attribution logic to determine which offer/channel prevails
    when a customer has multiple offers or comes through different channels.
    """
    logger = _get_logger()
    logger.info("Starting offer attribution logic...")

    try:
        # This is a simplified example. Real attribution logic would be complex,
        # potentially involving specific channel priorities, offer types, or recency.
        # Here, we assume the most recently created active offer prevails.

        # Find customers who have more than one active offer
        customers_with_multiple_active_offers = db.session.query(Offer.customer_id) \
            .filter(Offer.offer_status == 'Active') \
            .group_by(Offer.customer_id) \
            .having(db.func.count(Offer.offer_id) > 1) \
            .all()

        processed_customers_count = 0
        for row in customers_with_multiple_active_offers:
            customer_id = row.customer_id
            active_offers = db.session.query(Offer) \
                .filter_by(customer_id=customer_id, offer_status='Active') \
                .order_by(Offer.created_at.desc()) \
                .all()

            if not active_offers:
                continue

            # The first offer in the sorted list is the most recent active one (canonical)
            canonical_offer = active_offers[0]
            offers_to_deactivate = active_offers[1:]

            for offer in offers_to_deactivate:
                if offer.offer_status == 'Active': # Only change if currently active
                    offer.offer_status = 'Inactive' # Or 'Attributed_Out'
                    offer.updated_at = datetime.now()
                    logger.info(f"Offer {offer.offer_id} for customer {customer_id} marked Inactive due to attribution. Canonical: {canonical_offer.offer_id}")
            processed_customers_count += 1

        db.session.commit()
        logger.info(f"Offer attribution completed. Processed {processed_customers_count} customers with multiple offers.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during offer attribution: {e}", exc_info=True)
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during offer attribution: {e}", exc_info=True)
        raise

def update_offer_expiry_status():
    """
    FR13, FR37, FR38: Updates offer statuses based on expiry logic.
    - Offers for non-journey started customers expire based on offer end dates.
    - Offers with started loan application journeys expire if LAN validity is over.
    """
    logger = _get_logger()
    logger.info("Starting offer expiry status update...")

    try:
        current_date = datetime.now().date()
        updated_offers_count = 0

        # Rule 1: Offers for non-journey started customers (loan_application_number is NULL)
        # expire if their offer_end_date is in the past and they are currently 'Active'.
        expired_offers_no_lan = db.session.query(Offer) \
            .filter(Offer.loan_application_number.is_(None)) \
            .filter(Offer.offer_end_date < current_date) \
            .filter(Offer.offer_status == 'Active') \
            .all()

        for offer in expired_offers_no_lan:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.now()
            updated_offers_count += 1
            logger.info(f"Offer {offer.offer_id} (no LAN) expired based on end date {offer.offer_end_date}.")

        # Rule 2: Offers with started loan application journeys (loan_application_number is NOT NULL)
        # expire if the loan application journey is considered 'over' (e.g., rejected, expired).
        # This requires joining with customer_events or an application status table.
        # The BRD (Question 3) asks for clarification on LAN validity.
        # For this implementation, we'll assume a simple check: if an offer has a LAN,
        # and there's a 'REJECTED' or 'EXPIRED' event for that customer/LAN, mark the offer as expired.
        # This is a placeholder and needs precise business logic.

        # Find active offers with a loan application number
        active_offers_with_lan = db.session.query(Offer) \
            .filter(Offer.loan_application_number.isnot(None)) \
            .filter(Offer.offer_status == 'Active') \
            .all()

        for offer in active_offers_with_lan:
            # Check if there's a 'rejected' or 'expired' event for this LAN/customer
            # This logic might need to be more specific (e.g., event related to this specific LAN)
            rejection_or_expiry_event = db.session.query(CustomerEvent) \
                .filter(CustomerEvent.customer_id == offer.customer_id) \
                .filter(CustomerEvent.event_type.in_(['APP_STAGE_REJECTED', 'APP_STAGE_EXPIRED'])) \
                .filter(CustomerEvent.event_timestamp > offer.created_at) \
                .first()

            if rejection_or_expiry_event:
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.now()
                updated_offers_count += 1
                logger.info(f"Offer {offer.offer_id} (with LAN {offer.loan_application_number}) expired due to application status.")

        db.session.commit()
        logger.info(f"Offer expiry status update completed. {updated_offers_count} offers updated.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during offer expiry update: {e}", exc_info=True)
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during offer expiry update: {e}", exc_info=True)
        raise

def generate_reverse_feed_to_offermart():
    """
    FR8, NFR6: Pushes a daily reverse feed to Offermart, including Offer data updates from E-aggregators.
    This function extracts updated offer data and simulates sending it to Offermart.
    """
    logger = _get_logger()
    logger.info("Generating reverse feed to Offermart...")

    try:
        # Define a time window for updates, e.g., offers updated in the last 24 hours.
        # In a real system, this would be based on the last successful feed timestamp.
        time_window_start = datetime.now() - timedelta(days=1)

        updated_offers = db.session.query(Offer).filter(Offer.updated_at >= time_window_start).all()

        if not updated_offers:
            logger.info("No updated offers found for reverse feed to Offermart.")
            return

        # Prepare data in a format suitable for Offermart.
        # This structure would depend on the Offermart API/file format.
        feed_data = []
        for offer in updated_offers:
            feed_data.append({
                'offer_id': str(offer.offer_id),
                'customer_id': str(offer.customer_id),
                'offer_status': offer.offer_status,
                'loan_application_number': offer.loan_application_number,
                'updated_at': offer.updated_at.isoformat(),
                'attribution_channel': offer.attribution_channel,
                # Add other fields as required by Offermart
            })

        # Simulate sending data to Offermart (e.g., via API call, SFTP file upload)
        logger.info(f"Simulating sending {len(feed_data)} updated offers to Offermart.")
        # Example: off_mart_integration_service.send_offer_updates(feed_data)
        # Or: pd.DataFrame(feed_data).to_csv('offermart_reverse_feed.csv', index=False)

        logger.info("Reverse feed to Offermart generated successfully.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during reverse feed generation: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during reverse feed generation: {e}", exc_info=True)
        raise

def push_data_to_edw():
    """
    FR23, NFR8: Passes all data from LTFS Offer CDP to EDW daily by day end.
    This function extracts data from CDP tables and simulates pushing it to EDW.
    """
    logger = _get_logger()
    logger.info("Pushing data to EDW...")

    try:
        # Extract data from CDP tables. For EDW, typically all relevant data is pushed.
        customers = db.session.query(Customer).all()
        offers = db.session.query(Offer).all()
        customer_events = db.session.query(CustomerEvent).all()
        campaigns = db.session.query(Campaign).all()

        # Convert to pandas DataFrames for easier manipulation and export.
        # Exclude SQLAlchemy internal state attributes.
        customers_df = pd.DataFrame([c.__dict__ for c in customers if '_sa_instance_state' not in c.__dict__])
        offers_df = pd.DataFrame([o.__dict__ for o in offers if '_sa_instance_state' not in o.__dict__])
        events_df = pd.DataFrame([e.__dict__ for e in customer_events if '_sa_instance_state' not in e.__dict__])
        campaigns_df = pd.DataFrame([c.__dict__ for c in campaigns if '_sa_instance_state' not in c.__dict__])

        # Simulate data transformation and loading to EDW.
        # In a real scenario, this would involve:
        # - Selecting specific columns relevant for EDW.
        # - Renaming columns to match EDW schema.
        # - Handling data types and potential aggregations.
        # - Writing to a staging area or directly to EDW tables (e.g., via a data pipeline tool).
        logger.info(f"Simulating pushing {len(customers_df)} customers, {len(offers_df)} offers, "
                    f"{len(events_df)} events, and {len(campaigns_df)} campaigns to EDW.")

        # Example:
        # customers_df.to_sql('edw_customers_dim', edw_db_engine, if_exists='append', index=False)
        # offers_df.to_csv('edw_offers_fact.csv', index=False)

        logger.info("Data pushed to EDW successfully.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during EDW data push: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during EDW data push: {e}", exc_info=True)
        raise

def generate_moengage_file_data() -> pd.DataFrame:
    """
    FR25, FR39: Generates the data for the Moengage File in CSV format.
    This function prepares the data, which can then be downloaded via an API endpoint.
    It should exclude DND customers (FR21).
    Returns a pandas DataFrame containing the Moengage-formatted data.
    """
    logger = _get_logger()
    logger.info("Generating Moengage file data...")

    try:
        # Query active customers who are not DND and have active offers.
        # This query should be refined based on actual Moengage requirements for fields.
        moengage_eligible_data = db.session.query(Customer, Offer) \
            .join(Offer, Customer.customer_id == Offer.customer_id) \
            .filter(Customer.is_dnd == False) \
            .filter(Offer.offer_status == 'Active') \
            .all()

        if not moengage_eligible_data:
            logger.info("No eligible customers found for Moengage file generation.")
            return pd.DataFrame() # Return empty DataFrame

        moengage_records = []
        for customer, offer in moengage_eligible_data:
            # Construct the record based on Moengage's expected format.
            # This is a placeholder for actual Moengage fields and their mapping.
            moengage_records.append({
                'customer_id': str(customer.customer_id),
                'mobile_number': customer.mobile_number,
                'pan': customer.pan,
                'offer_id': str(offer.offer_id),
                'offer_type': offer.offer_type,
                'offer_end_date': offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                'customer_segment': customer.customer_segment,
                'propensity_flag': offer.propensity_flag,
                'attribution_channel': offer.attribution_channel,
                # Add other customer/offer attributes as needed by Moengage
            })

        moengage_df = pd.DataFrame(moengage_records)
        logger.info(f"Generated Moengage file data for {len(moengage_df)} records.")
        return moengage_df

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during Moengage file data generation: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during Moengage file data generation: {e}", exc_info=True)
        raise

def run_daily_batch_processes():
    """
    Orchestrates the daily batch processing pipeline.
    This function should be called by a scheduler (e.g., Celery beat, cron job).
    """
    logger = _get_logger()
    logger.info("--- Starting daily batch processing pipeline ---")

    try:
        # Step 1: Daily data ingestion from Offermart staging to CDP.
        # This is assumed to be handled by a separate ingestion task (e.g., in app/tasks/batch_ingestion.py).
        # If it were part of this file, it would involve reading from a staging table and inserting/updating
        # Customer and Offer records, including basic column-level validation (FR1).
        logger.info("Assuming daily data ingestion from Offermart staging is complete or handled by 'batch_ingestion.py'.")
        # Example if `batch_ingestion` was imported:
        # from app.tasks.batch_ingestion import ingest_offermart_data
        # ingest_offermart_data()

        # Step 2: Perform Deduplication (FR3, FR4, FR5)
        perform_deduplication()

        # Step 3: Apply Attribution Logic (FR20)
        apply_attribution_logic()

        # Step 4: Update Offer Expiry Status (FR13, FR37, FR38)
        update_offer_expiry_status()

        # Step 5: Generate Reverse Feed to Offermart (FR8)
        generate_reverse_feed_to_offermart()

        # Step 6: Push Data to EDW (FR23)
        push_data_to_edw()

        # Step 7: Enforce data retention policies (FR18, FR24)
        # This is explicitly mentioned in the RAG context for app/tasks/data_cleanup.py
        try:
            from app.tasks.data_cleanup import cleanup_old_data
            cleanup_old_data()
        except ImportError:
            logger.warning("Could not import app.tasks.data_cleanup. Skipping data cleanup.")
        except Exception as e:
            logger.error(f"Error calling data cleanup task: {e}", exc_info=True)

    except Exception as e:
        logger.critical(f"Daily batch processing pipeline failed: {e}", exc_info=True)
        # In a production system, this would trigger alerts (e.g., email, Slack).
    finally:
        # Ensure database session is closed even if errors occur
        if hasattr(db, 'session') and db.session.is_active:
            db.session.close()
        logger.info("--- Daily batch processing pipeline completed ---")


if __name__ == '__main__':
    # This block is for local testing/demonstration.
    # In a real Flask application, you would typically run this via a Flask CLI command
    # or a Celery worker, ensuring the Flask app context and database are properly initialized.
    print("Running batch processes (this might require a Flask app context and DB setup).")
    print("If you see 'WARNING: Could not import app.extensions or app.models. Using mock objects.',")
    print("this script is running in standalone mode with mocked DB interactions.")
    print("For full functionality, run within a Flask application context.")

    # For standalone execution with mocks:
    run_daily_batch_processes()