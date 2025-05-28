import logging
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date
from sqlalchemy.exc import SQLAlchemyError

# Attempt to import Flask extensions and models.
# This allows the script to be run standalone for testing,
# but warns that full functionality requires a Flask app context.
try:
    from app.extensions import db
    from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog
    # Assuming other necessary models like OffermartStaging, EDWFeedLog etc. would exist
    # For this exercise, we'll simulate their interaction.
except ImportError:
    # Mock db and models for standalone execution without Flask app context
    class MockDB:
        def session(self):
            return self

        def add(self, obj):
            logging.warning(f"MockDB: Adding {obj.__class__.__name__}")

        def commit(self):
            logging.warning("MockDB: Committing changes (mock)")

        def rollback(self):
            logging.warning("MockDB: Rolling back changes (mock)")

        def query(self, model):
            return MockQuery(model)

    class MockQuery:
        def __init__(self, model):
            self.model = model
            self.filters = []

        def filter(self, *args):
            self.filters.extend(args)
            return self

        def delete(self, synchronize_session=False):
            logging.warning(f"MockDB: Deleting from {self.model.__name__} with filters: {self.filters} (mock)")
            return 0 # Return 0 rows affected for mock

        def all(self):
            logging.warning(f"MockDB: Querying all from {self.model.__name__} (mock)")
            return []

        def first(self):
            logging.warning(f"MockDB: Querying first from {self.model.__name__} (mock)")
            return None

    db = MockDB()

    class MockCustomer:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def __repr__(self): return f"<MockCustomer {self.customer_id}>"
    class MockOffer:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def __repr__(self): return f"<MockOffer {self.offer_id}>"
    class MockCustomerEvent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def __repr__(self): return f"<MockCustomerEvent {self.event_id}>"
    class MockCampaign:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def __repr__(self): return f"<MockCampaign {self.campaign_id}>"
    class MockDataIngestionLog:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def __repr__(self): return f"<MockDataIngestionLog {self.log_id}>"

    Customer = MockCustomer
    Offer = MockOffer
    CustomerEvent = MockCustomerEvent
    Campaign = MockCampaign
    DataIngestionLog = MockDataIngestionLog

    logging.warning("WARNING: Could not import app.extensions or app.models. Using mock objects.")
    logging.warning("For full functionality, ensure this script runs within a Flask application context.")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ingest_offermart_data():
    """
    FR7: The system shall receive Offer data and Customer data from Offermart daily by creating a staging area (Offer DB to CDP DB).
    NFR5: The system shall handle daily data pushes from Offermart to CDP.
    FR1: The system shall perform basic column-level validation when moving data from Offermart to CDP.
    """
    logger.info("--- Starting Offermart data ingestion ---")
    try:
        # Simulate receiving data from Offermart.
        # In a real scenario, this would involve:
        # 1. Reading from a shared file system (CSV/Excel)
        # 2. Connecting to an Offermart database directly
        # 3. Calling an Offermart API
        # For this simulation, we'll assume a list of dicts.

        # Example mock data (replace with actual data source)
        mock_offermart_customers = [
            {"mobile_number": "9876543210", "pan": "ABCDE1234F", "customer_segment": "C1", "offer_type": "Fresh", "offer_end_date": "2024-12-31"},
            {"mobile_number": "9988776655", "pan": "FGHIJ5678K", "customer_segment": "C2", "offer_type": "Enrich", "offer_end_date": "2024-11-30"},
            {"mobile_number": "9876543210", "pan": "ABCDE1234F", "customer_segment": "C1", "offer_type": "New-old", "offer_end_date": "2024-10-15"}, # Duplicate customer
        ]

        new_customers_count = 0
        new_offers_count = 0
        updated_offers_count = 0
        errors = []

        for record in mock_offermart_customers:
            mobile_number = record.get("mobile_number")
            pan = record.get("pan")
            offer_type = record.get("offer_type")
            offer_end_date_str = record.get("offer_end_date")

            # Basic validation (FR1)
            if not mobile_number or not pan or not offer_type or not offer_end_date_str:
                errors.append(f"Skipping record due to missing essential data: {record}")
                continue

            try:
                offer_end_date = datetime.strptime(offer_end_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append(f"Skipping record due to invalid date format: {record}")
                continue

            try:
                # Find or create customer
                customer = db.session.query(Customer).filter(
                    (Customer.mobile_number == mobile_number) |
                    (Customer.pan == pan) # Add other identifiers as per FR2
                ).first()

                if not customer:
                    customer = Customer(
                        mobile_number=mobile_number,
                        pan=pan,
                        customer_segment=record.get("customer_segment"),
                        # Add other customer attributes as needed
                    )
                    db.session.add(customer)
                    db.session.flush() # Flush to get customer_id for offer
                    new_customers_count += 1
                    logger.info(f"Created new customer: {customer.customer_id}")
                else:
                    # Update existing customer attributes if necessary
                    customer.customer_segment = record.get("customer_segment", customer.customer_segment)
                    customer.updated_at = datetime.now()
                    logger.info(f"Updated existing customer: {customer.customer_id}")

                # Create or update offer (FR6: update old offers with new data)
                # This logic might need refinement based on how "old offers" are identified
                # and what "new data" means for an offer. For simplicity, we'll add a new offer
                # if it's a 'Fresh' offer or if no matching offer exists for the customer/type.
                # A more robust solution would involve checking offer_id or specific offer criteria.
                existing_offer = db.session.query(Offer).filter(
                    Offer.customer_id == customer.customer_id,
                    Offer.offer_type == offer_type,
                    Offer.offer_status == 'Active' # Assuming we update active offers
                ).first()

                if existing_offer:
                    # Update existing offer (FR6)
                    existing_offer.offer_end_date = offer_end_date
                    existing_offer.updated_at = datetime.now()
                    updated_offers_count += 1
                    logger.info(f"Updated existing offer: {existing_offer.offer_id} for customer {customer.customer_id}")
                else:
                    # Create new offer
                    new_offer = Offer(
                        customer_id=customer.customer_id,
                        offer_type=offer_type,
                        offer_status='Active', # Default status
                        offer_start_date=datetime.now().date(),
                        offer_end_date=offer_end_date,
                        # Add other offer attributes
                    )
                    db.session.add(new_offer)
                    new_offers_count += 1
                    logger.info(f"Created new offer: {new_offer.offer_id} for customer {customer.customer_id}")

                db.session.commit()

            except SQLAlchemyError as e:
                db.session.rollback()
                errors.append(f"Database error processing record {record}: {e}")
                logger.error(f"Database error during ingestion: {e}")
            except Exception as e:
                db.session.rollback()
                errors.append(f"Unexpected error processing record {record}: {e}")
                logger.error(f"Unexpected error during ingestion: {e}")

        logger.info(f"--- Offermart data ingestion completed. New customers: {new_customers_count}, New offers: {new_offers_count}, Updated offers: {updated_offers_count}, Errors: {len(errors)} ---")
        if errors:
            logger.warning(f"Ingestion errors: {errors}")

    except Exception as e:
        logger.error(f"Failed to ingest Offermart data: {e}")
        db.session.rollback() # Ensure rollback on higher level errors

def perform_deduplication():
    """
    FR3: The system shall perform deduplication within all Consumer Loan products.
    FR4: The system shall perform deduplication against the live book (Customer 360).
    FR5: The system shall dedupe Top-up loan offers only within other Top-up offers.
    """
    logger.info("--- Starting customer deduplication ---")
    try:
        # This is a complex process. A simplified approach:
        # 1. Identify potential duplicates based on key identifiers.
        # 2. Apply rules to determine the 'master' record.
        # 3. Merge or link duplicate records to the master.

        # For demonstration, we'll just log potential duplicates.
        # A real implementation would involve sophisticated SQL queries or a dedicated deduplication service.

        # Example: Find customers with same mobile number but different customer_id (if any were created separately)
        # Or, more realistically, identify customers that might have been ingested with different identifiers
        # but resolve to the same person.

        # This query is a simplified example to find potential duplicates based on mobile number
        # In a real scenario, this would involve more complex joins and logic across multiple identifiers.
        potential_duplicates = db.session.query(Customer.mobile_number, func.count(Customer.customer_id).label('count')) \
            .group_by(Customer.mobile_number) \
            .having(func.count(Customer.customer_id) > 1) \
            .all()

        deduplicated_count = 0
        if potential_duplicates:
            logger.info(f"Found {len(potential_duplicates)} mobile numbers with multiple customer entries.")
            for mobile, count in potential_duplicates:
                logger.info(f"Mobile: {mobile} has {count} entries. Needs deduplication.")
                # In a real scenario, retrieve these customers, apply merge logic (e.g., keep oldest,
                # or one with most complete data), re-assign offers/events to the master customer_id,
                # and mark/delete duplicate customer records.
                # Example:
                # customers_to_dedupe = db.session.query(Customer).filter(Customer.mobile_number == mobile).order_by(Customer.created_at).all()
                # master_customer = customers_to_dedupe[0]
                # for dupe_customer in customers_to_dedupe[1:]:
                #     # Reassign offers and events
                #     db.session.query(Offer).filter(Offer.customer_id == dupe_customer.customer_id).update({"customer_id": master_customer.customer_id})
                #     db.session.query(CustomerEvent).filter(CustomerEvent.customer_id == dupe_customer.customer_id).update({"customer_id": master_customer.customer_id})
                #     db.session.delete(dupe_customer)
                #     deduplicated_count += 1
                # db.session.commit()
        else:
            logger.info("No immediate mobile number duplicates found in this run.")

        # FR4: Deduplication against live book (Customer 360) - This would involve an external API call or DB link
        logger.info("Simulating deduplication against Customer 360 live book (external system interaction).")

        # FR5: Top-up loan offers deduplication - specific logic for offer types
        logger.info("Simulating specific deduplication for Top-up loan offers.")

        logger.info(f"--- Customer deduplication completed. {deduplicated_count} records processed. ---")
    except SQLAlchemyError as e:
        logger.error(f"Database error during deduplication: {e}")
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to perform deduplication: {e}")
        db.session.rollback()

def apply_attribution_logic():
    """
    FR20: The system shall apply attribution logic to determine which offer/channel prevails
          when a customer has multiple offers or comes through different channels.
    """
    logger.info("--- Starting offer attribution logic ---")
    try:
        # Identify customers with multiple active offers
        customers_with_multiple_offers = db.session.query(Offer.customer_id, func.count(Offer.offer_id).label('offer_count')) \
            .filter(Offer.offer_status == 'Active') \
            .group_by(Offer.customer_id) \
            .having(func.count(Offer.offer_id) > 1) \
            .all()

        attributed_offers_count = 0
        for customer_id, offer_count in customers_with_multiple_offers:
            logger.info(f"Customer {customer_id} has {offer_count} active offers. Applying attribution.")
            customer_offers = db.session.query(Offer).filter(
                Offer.customer_id == customer_id,
                Offer.offer_status == 'Active'
            ).order_by(Offer.created_at.desc()).all() # Example: newest offer prevails

            if customer_offers:
                # Simple attribution: The newest offer prevails. Others are marked inactive.
                # In a real scenario, this would involve complex business rules (e.g., product priority, channel priority, offer value).
                prevailing_offer = customer_offers[0]
                logger.info(f"Prevailing offer for customer {customer_id}: {prevailing_offer.offer_id} (Type: {prevailing_offer.offer_type})")

                for offer in customer_offers[1:]:
                    if offer.offer_status == 'Active': # Only update if still active
                        offer.offer_status = 'Inactive' # Or 'Attributed_Out'
                        offer.updated_at = datetime.now()
                        attributed_offers_count += 1
                        logger.info(f"Marked offer {offer.offer_id} as Inactive due to attribution.")
            db.session.commit()

        logger.info(f"--- Offer attribution logic completed. {attributed_offers_count} offers updated. ---")
    except SQLAlchemyError as e:
        logger.error(f"Database error during attribution: {e}")
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to apply attribution logic: {e}")
        db.session.rollback()

def update_offer_expiry_status():
    """
    FR13: The system shall prevent modification of customer offers with started loan application journeys until the loan application is either expired or rejected.
    FR15: The system shall maintain flags for Offer statuses: Active, Inactive, and Expired, based on defined business logic.
    FR37: The system shall implement expiry logic where offers for non-journey started customers depend on offer end dates, allowing replenishment of expired offers.
    FR38: The system shall mark offers as expired within the offers data if the Loan Application Number (LAN) validity post loan application journey start date is over.
    """
    logger.info("--- Starting offer expiry status update ---")
    try:
        current_date = datetime.now().date()
        expired_count = 0

        # Logic for non-journey started customers (FR37)
        # Offers whose offer_end_date has passed and no loan_application_number
        offers_to_expire_by_date = db.session.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.offer_end_date < current_date,
            Offer.loan_application_number.is_(None) # No journey started
        ).all()

        for offer in offers_to_expire_by_date:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.now()
            expired_count += 1
            logger.info(f"Offer {offer.offer_id} expired by date for customer {offer.customer_id}.")

        # Logic for journey started customers (FR38)
        # This requires knowing the LAN validity period, which is not specified.
        # Assuming a placeholder validity period (e.g., 30 days after LAN creation/update)
        # In a real system, this would likely involve checking a `loan_applications` table
        # or a specific `lan_valid_until` field.
        lan_validity_days = 30 # Placeholder
        offers_to_expire_by_lan = db.session.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.loan_application_number.isnot(None),
            # This condition is a placeholder. It assumes 'updated_at' reflects LAN journey start/update.
            # A more accurate check would involve a dedicated 'loan_journey_start_date' or 'lan_valid_until' field.
            cast(Offer.updated_at, Date) < (current_date - timedelta(days=lan_validity_days))
        ).all()

        for offer in offers_to_expire_by_lan:
            # Before expiring, check if the loan application is truly expired/rejected (FR13)
            # This would involve querying LOS or an internal loan application status table.
            # For simulation, we'll assume it's expired if it meets the date criteria.
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.now()
            expired_count += 1
            logger.info(f"Offer {offer.offer_id} expired by LAN validity for customer {offer.customer_id}.")

        db.session.commit()
        logger.info(f"--- Offer expiry status update completed. {expired_count} offers marked as expired. ---")
    except SQLAlchemyError as e:
        logger.error(f"Database error during offer expiry update: {e}")
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to update offer expiry status: {e}")
        db.session.rollback()

def generate_and_push_reverse_feed():
    """
    FR8: The system shall push a daily reverse feed to Offermart, including Offer data updates from E-aggregators, on an hourly/daily basis.
    NFR6: The system shall handle hourly/daily reverse feeds from CDP to Offermart.
    """
    logger.info("--- Starting reverse feed generation and push to Offermart ---")
    try:
        # Query data that needs to be sent back to Offermart.
        # This could include:
        # - Updated offer statuses (e.g., Expired, Inactive due to attribution)
        # - Offers updated by E-aggregators (if tracked with a specific flag/source)
        # - Customer updates relevant to Offermart (e.g., DND status)

        # For simulation, let's get all offers updated in the last 24 hours.
        yesterday = datetime.now() - timedelta(days=1)
        updated_offers = db.session.query(Offer).filter(
            Offer.updated_at >= yesterday
        ).all()

        feed_data = []
        for offer in updated_offers:
            customer = db.session.query(Customer).get(offer.customer_id)
            if customer:
                feed_data.append({
                    "offer_id": str(offer.offer_id),
                    "customer_id": str(customer.customer_id),
                    "mobile_number": customer.mobile_number,
                    "pan": customer.pan,
                    "offer_type": offer.offer_type,
                    "offer_status": offer.offer_status,
                    "loan_application_number": offer.loan_application_number,
                    "updated_at": offer.updated_at.isoformat()
                })

        if feed_data:
            # Simulate pushing data to Offermart.
            # This would typically involve:
            # 1. Generating a CSV/Excel file and placing it in a shared location.
            # 2. Calling an Offermart API to push updates.
            # 3. Direct database write to an Offermart staging table.
            logger.info(f"Generated reverse feed with {len(feed_data)} records. Simulating push to Offermart.")
            # Example: write to a dummy file
            # with open(f"offermart_reverse_feed_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv", "w") as f:
            #     # Write CSV header and data
            #     pass
        else:
            logger.info("No updated offers to include in reverse feed.")

        logger.info("--- Reverse feed generation and push completed ---")
    except SQLAlchemyError as e:
        logger.error(f"Database error during reverse feed generation: {e}")
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to generate and push reverse feed: {e}")

def push_data_to_edw():
    """
    FR23: The system shall pass all data, including campaign data, from LTFS Offer CDP to EDW daily by day end.
    NFR8: The system shall perform daily data transfer from LTFS Offer CDP to EDW by day end.
    """
    logger.info("--- Starting data push to EDW ---")
    try:
        # Query all relevant data from CDP for EDW.
        # This could be a full dump or incremental changes since last push.
        # For simplicity, we'll simulate querying all customers, offers, events, and campaigns.

        customers_data = db.session.query(Customer).all()
        offers_data = db.session.query(Offer).all()
        events_data = db.session.query(CustomerEvent).all()
        campaigns_data = db.session.query(Campaign).all()

        # Prepare data for EDW (e.g., convert to Pandas DataFrames, then to CSV/Parquet/JSON)
        # In a real scenario, this might involve complex ETL transformations.
        logger.info(f"Preparing {len(customers_data)} customers, {len(offers_data)} offers, {len(events_data)} events, {len(campaigns_data)} campaigns for EDW.")

        # Simulate pushing data to EDW.
        # This would typically involve:
        # 1. Writing files to a data lake/warehouse staging area (e.g., S3, HDFS).
        # 2. Using a data integration tool (e.g., Apache NiFi, Airflow, custom scripts).
        # 3. Direct database connection to EDW.
        logger.info("Simulating data transfer to EDW.")

        logger.info("--- Data push to EDW completed ---")
    except SQLAlchemyError as e:
        logger.error(f"Database error during EDW data push: {e}")
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to push data to EDW: {e}")

def enforce_data_retention():
    """
    FR18: The system shall maintain offer history for the past 06 months for reference purposes. (NFR3)
    FR24: The system shall maintain all data in LTFS Offer CDP for previous 3 months before deletion. (NFR4)
    """
    logger.info("--- Starting data retention enforcement ---")
    try:
        current_date = datetime.now()

        # Retain offer history for 6 months (FR18, NFR3)
        six_months_ago = current_date - timedelta(days=6 * 30) # Approximate 6 months
        offers_deleted_count = db.session.query(Offer).filter(
            Offer.created_at < six_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {offers_deleted_count} old offers (older than 6 months).")

        # Retain all other CDP data for 3 months (FR24, NFR4)
        three_months_ago = current_date - timedelta(days=3 * 30) # Approximate 3 months

        # Note: Deleting customers directly might violate foreign key constraints
        # if their offers/events are still within retention period.
        # A safer approach is to delete child records first, or mark customers for archival.
        # For this exercise, we'll assume cascading deletes or that related data is also old enough.

        events_deleted_count = db.session.query(CustomerEvent).filter(
            CustomerEvent.created_at < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {events_deleted_count} old customer events (older than 3 months).")

        campaigns_deleted_count = db.session.query(Campaign).filter(
            Campaign.created_at < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {campaigns_deleted_count} old campaigns (older than 3 months).")

        logs_deleted_count = db.session.query(DataIngestionLog).filter(
            DataIngestionLog.upload_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {logs_deleted_count} old ingestion logs (older than 3 months).")

        # Customers: Only delete if they have no active offers or recent events.
        # This is a complex rule. For simplicity, we'll skip direct customer deletion here
        # or assume a separate archival process. If a customer has no associated data
        # (offers, events) within the retention period, they could be deleted.
        # Example (requires careful consideration of related data):
        # customers_to_delete = db.session.query(Customer).filter(
        #     ~Customer.offers.any(Offer.created_at >= three_months_ago),
        #     ~Customer.events.any(CustomerEvent.created_at >= three_months_ago),
        #     Customer.created_at < three_months_ago
        # ).delete(synchronize_session=False)
        # logger.info(f"Deleted {customers_to_delete} old customer records (older than 3 months and no recent activity).")

        db.session.commit()
        logger.info("--- Data retention enforcement completed ---")
    except SQLAlchemyError as e:
        logger.error(f"Database error during data retention: {e}")
        db.session.rollback()
    except Exception as e:
        logger.error(f"Failed to enforce data retention: {e}")
        db.session.rollback()


def run_daily_batch_processes():
    """
    Orchestrates the daily batch processing pipeline for the CDP.
    This function should be scheduled to run daily (e.g., via Celery, cron job).
    """
    logger.info("--- Starting daily batch processing pipeline ---")

    # Step 1: Ingest daily data from Offermart
    ingest_offermart_data()

    # Step 2: Perform deduplication on newly ingested and existing data
    perform_deduplication()

    # Step 3: Apply attribution logic to offers
    apply_attribution_logic()

    # Step 4: Update offer expiry statuses
    update_offer_expiry_status()

    # Step 5: Generate and push daily reverse feed to Offermart
    generate_and_push_reverse_feed()

    # Step 6: Push all relevant CDP data to EDW
    push_data_to_edw()

    # Step 7: Enforce data retention policies
    enforce_data_retention()

    logger.info("--- Daily batch processing pipeline completed ---")


if __name__ == '__main__':
    # This block is for local testing/demonstration.
    # In a real Flask application, you would typically run this via a Flask CLI command
    # or a Celery worker, ensuring the Flask app context and database are properly initialized.
    print("Running batch processes (this might require a Flask app context and DB setup).")
    print("If you see 'WARNING: Could not import app.extensions or app.models. Using mock objects.',")
    print("this script is running in standalone mode with mocked DB interactions.")
    print("For full functionality, run within a Flask application context.")

    # Example of how to run within a Flask app context (if app is defined)
    # from app import create_app
    # app = create_app()
    # with app.app_context():
    #     run_daily_batch_processes()

    # For standalone testing with mocks:
    run_daily_batch_processes()