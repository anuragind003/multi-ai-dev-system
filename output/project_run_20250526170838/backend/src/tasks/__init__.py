import csv
import io
import logging
from datetime import datetime, timedelta
import uuid

# --- Mock/Placeholder for DB and Models ---
# In a real Flask application, 'db' would be an instance of SQLAlchemy,
# and models would be imported from a dedicated 'models.py' file.
# For this exercise, we define mock classes to make the code runnable
# and demonstrate the intended interactions.

class MockDB:
    """A mock SQLAlchemy DB object for demonstration purposes."""
    def __init__(self):
        self.session = self.MockSession()

    class MockSession:
        """A mock SQLAlchemy session."""
        def add(self, obj):
            logging.debug(f"MockDB: Added {obj.__class__.__name__}")
        def add_all(self, objs):
            logging.debug(f"MockDB: Added multiple {objs[0].__class__.__name__ if objs else 'objects'}")
        def commit(self):
            logging.info("MockDB: Committed transaction")
        def rollback(self):
            logging.warning("MockDB: Rolled back transaction")
        def close(self):
            logging.debug("MockDB: Closed session")
        def query(self, model):
            return self.MockQuery(model)

    class MockQuery:
        """A mock SQLAlchemy query object."""
        def __init__(self, model):
            self.model = model
        def filter(self, *args, **kwargs):
            return self
        def filter_by(self, *args, **kwargs):
            return self
        def all(self):
            return [] # Mock no results
        def first(self):
            return None # Mock no result
        def update(self, values, synchronize_session=False):
            logging.info(f"MockDB: Updated {self.model.__name__} with {values}")
            return 0 # Mock no rows affected
        def delete(self):
            logging.info(f"MockDB: Deleted {self.model.__name__} records")
            return 0 # Mock no rows affected

# Mock Models based on the provided database schema
class Customer:
    def __init__(self, customer_id, mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None, loan_application_number=None, dnd_flag=False, segment=None, created_at=None, updated_at=None):
        self.customer_id = customer_id or str(uuid.uuid4())
        self.mobile_number = mobile_number
        self.pan_number = pan_number
        self.aadhaar_number = aadhaar_number
        self.ucid_number = ucid_number
        self.loan_application_number = loan_application_number
        self.dnd_flag = dnd_flag
        self.segment = segment
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class Offer:
    def __init__(self, offer_id, customer_id, offer_type, offer_status, propensity, start_date, end_date, channel, created_at=None, updated_at=None):
        self.offer_id = offer_id or str(uuid.uuid4())
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.propensity = propensity
        self.start_date = start_date
        self.end_date = end_date
        self.channel = channel
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class Event:
    def __init__(self, event_id, customer_id, event_type, event_source, event_timestamp, event_details, created_at=None):
        self.event_id = event_id or str(uuid.uuid4())
        self.customer_id = customer_id
        self.event_type = event_type
        self.event_source = event_source
        self.event_timestamp = event_timestamp
        self.event_details = event_details
        self.created_at = created_at or datetime.now()

class CampaignMetric:
    def __init__(self, metric_id, campaign_unique_id, campaign_name, campaign_date, attempted_count, sent_success_count, failed_count, conversion_rate, created_at=None):
        self.metric_id = metric_id or str(uuid.uuid4())
        self.campaign_unique_id = campaign_unique_id
        self.campaign_name = campaign_name
        self.campaign_date = campaign_date
        self.attempted_count = attempted_count
        self.sent_success_count = sent_success_count
        self.failed_count = failed_count
        self.conversion_rate = conversion_rate
        self.created_at = created_at or datetime.now()

class IngestionLog:
    def __init__(self, log_id, file_name, upload_timestamp, status, error_description=None):
        self.log_id = log_id or str(uuid.uuid4())
        self.file_name = file_name
        self.upload_timestamp = upload_timestamp or datetime.now()
        self.status = status
        self.error_description = error_description

# Instantiate the mock DB
db = MockDB()

# --- End Mock/Placeholder ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _get_db_session():
    """
    Helper to get a database session.
    In a real Flask app, this would typically be `db.session` if within an app context,
    or a new session created from `db.engine` for background tasks.
    """
    return db.session

def _log_ingestion_status(log_id: str, file_name: str, status: str, error_description: str = None):
    """Logs the status of a data ingestion process to the IngestionLog table."""
    session = _get_db_session()
    try:
        log_entry = IngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status=status,
            error_description=error_description
        )
        session.add(log_entry)
        session.commit()
        logging.info(f"Ingestion log recorded: {file_name} - {status}")
    except Exception as e:
        session.rollback()
        logging.error(f"Failed to record ingestion log for {file_name}: {e}")
    finally:
        session.close()

def process_uploaded_customer_data(log_id: str, file_content: str, file_name: str, loan_type: str):
    """
    Processes an uploaded CSV file containing customer details.
    Performs basic validation, inserts/updates customers, and logs results.
    (FR35, FR36, FR37, FR38, FR1, NFR3)
    """
    session = _get_db_session()
    success_count = 0
    error_count = 0
    error_rows = []

    try:
        csv_file = io.StringIO(file_content)
        reader = csv.DictReader(csv_file)

        # Example required columns for basic validation (FR1, NFR3)
        required_columns = ['mobile_number', 'pan_number', 'aadhaar_number']

        for i, row in enumerate(reader):
            row_num = i + 1
            # Basic column-level validation
            if not all(row.get(col) for col in required_columns):
                error_rows.append({'row_number': row_num, 'data': row, 'Error Desc': 'Missing required fields'})
                error_count += 1
                continue

            try:
                # Deduplication check and upsert logic (simplified for this file)
                # In a real scenario, this would involve complex queries and potentially
                # a dedicated deduplication service.
                customer_identifiers = {
                    'mobile_number': row.get('mobile_number'),
                    'pan_number': row.get('pan_number'),
                    'aadhaar_number': row.get('aadhaar_number'),
                    'ucid_number': row.get('ucid_number'),
                    'loan_application_number': row.get('loan_application_number')
                }

                existing_customer = None
                # In a real app, query for existing customer using any of the identifiers
                # For example:
                # existing_customer = session.query(Customer).filter(
                #     (Customer.mobile_number == customer_identifiers['mobile_number']) |
                #     (Customer.pan_number == customer_identifiers['pan_number']) |
                #     (Customer.aadhaar_number == customer_identifiers['aadhaar_number'])
                # ).first()

                if existing_customer:
                    # Update existing customer (FR8 - implied for customer data)
                    # Example: existing_customer.segment = row.get('segment', existing_customer.segment)
                    # session.add(existing_customer)
                    logging.info(f"Updating existing customer (mock): {existing_customer.customer_id}")
                else:
                    new_customer = Customer(
                        customer_id=str(uuid.uuid4()),
                        mobile_number=customer_identifiers.get('mobile_number'),
                        pan_number=customer_identifiers.get('pan_number'),
                        aadhaar_number=customer_identifiers.get('aadhaar_number'),
                        ucid_number=customer_identifiers.get('ucid_number'),
                        loan_application_number=customer_identifiers.get('loan_application_number'),
                        segment=row.get('segment'),
                        dnd_flag=row.get('dnd_flag', 'FALSE').upper() == 'TRUE'
                    )
                    session.add(new_customer)
                success_count += 1

            except Exception as e:
                error_rows.append({'row_number': row_num, 'data': row, 'Error Desc': str(e)})
                error_count += 1

        session.commit() # Commit all new/updated customers
        _log_ingestion_status(log_id, file_name, 'SUCCESS')
        logging.info(f"Successfully processed {success_count} records from {file_name}. Errors: {error_count}")

        # After initial ingestion, a comprehensive deduplication task might be triggered
        # run_deduplication_logic() # This would be a separate call, possibly async

        return {
            'status': 'success',
            'success_count': success_count,
            'error_count': error_count,
            'error_details': error_rows # For generating error file (FR38)
        }

    except Exception as e:
        session.rollback()
        _log_ingestion_status(log_id, file_name, 'FAILED', str(e))
        logging.error(f"An error occurred during processing {file_name}: {e}")
        return {
            'status': 'failed',
            'success_count': 0,
            'error_count': error_count,
            'error_details': error_rows,
            'system_error': str(e)
        }
    finally:
        session.close()

def run_deduplication_logic():
    """
    Applies comprehensive deduplication logic across all Consumer Loan products.
    (FR3, FR4, FR5, FR6)
    This is a complex scheduled task.
    """
    session = _get_db_session()
    try:
        logging.info("Starting comprehensive deduplication process...")
        # Placeholder for actual deduplication logic:
        # 1. Identify potential duplicates (Mobile, PAN, Aadhaar, UCID, LAN).
        # 2. Apply rules (e.g., Top-up offers only within other Top-up offers).
        # 3. Deduplicate against 'live book' (Customer 360) - requires external API/data access.
        # 4. Merge or mark duplicate records, updating related offers/events to point to master.
        logging.info("Deduplication process completed (placeholder).")
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred during deduplication: {e}")
    finally:
        session.close()

def update_offer_statuses():
    """
    Scheduled task to update offer statuses based on business logic.
    (FR16, FR41, FR42, FR43)
    """
    session = _get_db_session()
    try:
        current_date = datetime.now().date()

        # FR41: Mark offers as expired based on offer end dates for non-journey started customers.
        # This would involve a join with Customer and Event/Loan Application tables to check journey status.
        # For mock, a simplified update:
        expired_offers_count = session.query(Offer).filter(
            Offer.end_date < current_date,
            Offer.offer_status == 'Active'
            # Add condition for 'non-journey started customers'
        ).update({'offer_status': 'Expired', 'updated_at': datetime.now()}, synchronize_session=False)
        logging.info(f"Marked {expired_offers_count} offers as 'Expired' (end date passed).")

        # FR43: Mark offers as expired for journey started customers whose LAN validity is over.
        # This requires specific business logic for LAN validity (Q16).
        # Placeholder for this complex update.
        logging.info("Checking and marking offers expired for journey-started customers (placeholder).")

        # FR42: Check for and replenish new offers for non-journey started customers whose previous offers have expired.
        # This would involve identifying eligible customers and generating new offers.
        # Example: _generate_new_offer_for_customer(customer_id)
        logging.info("Replenishing new offers for eligible customers (placeholder).")

        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred during offer status update: {e}")
    finally:
        session.close()

def generate_moengage_export_file():
    """
    Generates the Moengage format CSV file for campaign export.
    (FR31, FR44, FR23, FR21)
    """
    session = _get_db_session()
    output = io.StringIO()
    writer = csv.writer(output)

    # Moengage requires specific columns. Placeholder for actual column names.
    header = ['customer_id', 'mobile_number', 'offer_id', 'offer_type', 'offer_status', 'propensity', 'campaign_id', 'channel']
    writer.writerow(header)

    try:
        # Query active customers with active offers, excluding DND customers (FR23)
        # Apply attribution logic (FR21) if multiple offers exist for a customer.
        # For mock, return some dummy data.
        mock_data = [
            (Customer(customer_id='cust_001', mobile_number='9876543210', dnd_flag=False),
             Offer(offer_id='offer_A', customer_id='cust_001', offer_type='Preapproved', offer_status='Active', propensity='High', start_date=datetime.now().date(), end_date=datetime.now().date() + timedelta(days=7), channel='SMS')),
            (Customer(customer_id='cust_002', mobile_number='9988776655', dnd_flag=False),
             Offer(offer_id='offer_B', customer_id='cust_002', offer_type='Loyalty', offer_status='Active', propensity='Medium', start_date=datetime.now().date(), end_date=datetime.now().date() + timedelta(days=14), channel='Email'))
        ]

        for customer, offer in mock_data:
            if not customer.dnd_flag: # Apply DND check (FR23)
                campaign_id = f"CAMPAIGN_{datetime.now().strftime('%Y%m%d')}"
                row = [
                    customer.customer_id,
                    customer.mobile_number,
                    offer.offer_id,
                    offer.offer_type,
                    offer.offer_status,
                    offer.propensity,
                    campaign_id,
                    offer.channel
                ]
                writer.writerow(row)

        logging.info("Moengage export file generated successfully.")
        return output.getvalue()

    except Exception as e:
        logging.error(f"An error occurred during Moengage export generation: {e}")
        return None
    finally:
        session.close()

def export_data_to_edw():
    """
    Pushes all relevant data from LTFS Offer CDP to EDW daily.
    (FR27)
    """
    session = _get_db_session()
    try:
        logging.info("Starting daily data export to EDW...")
        # This would involve querying various tables (customers, offers, events, campaign_metrics)
        # and formatting the data for EDW, likely via a file transfer or direct database link (Q10).
        logging.info("Data prepared for EDW. Transfer mechanism (e.g., SFTP, direct DB link) would be invoked here (placeholder).")
        logging.info("Daily data export to EDW completed.")
    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred during EDW export: {e}")
    finally:
        session.close()

def export_reverse_feed_to_offermart():
    """
    Pushes daily reverse feed to Offermart, including Offer data updates from E-aggregators.
    (FR10)
    """
    session = _get_db_session()
    try:
        logging.info("Starting daily reverse feed export to Offermart...")
        # Query offers that have been updated or created recently, especially from E-aggregators.
        # Format data according to Offermart's requirements.
        logging.info("Reverse feed data prepared for Offermart. Transfer mechanism would be invoked here (placeholder).")
        logging.info("Daily reverse feed export to Offermart completed.")
    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred during Offermart reverse feed export: {e}")
    finally:
        session.close()

def cleanup_old_data():
    """
    Scheduled task to enforce data retention policies.
    (FR19, FR28, NFR8, NFR9)
    """
    session = _get_db_session()
    try:
        # FR28, NFR9: Maintain all data in LTFS Offer CDP for previous 3 months before deletion.
        three_months_ago = datetime.now() - timedelta(days=90)
        six_months_ago = datetime.now() - timedelta(days=180) # For FR19

        # Delete old events
        deleted_events_count = session.query(Event).filter(Event.created_at < three_months_ago).delete(synchronize_session=False)
        logging.info(f"Deleted {deleted_events_count} old events (older than 3 months).")

        # Delete old offers (older than 6 months for history, but 3 months for general data retention)
        # This implies that if 'all data' is 3 months, then offer history is also 3 months.
        # If 6 months history is critical, a separate archival mechanism might be needed.
        # Sticking to 3 months for hard deletion based on FR28.
        deleted_offers_count = session.query(Offer).filter(Offer.created_at < three_months_ago).delete(synchronize_session=False)
        logging.info(f"Deleted {deleted_offers_count} old offers (older than 3 months).")

        # Delete old customers (only if they have no active offers, events, or ongoing journeys)
        # This requires careful joins and subqueries to ensure data integrity.
        # For now, a placeholder.
        logging.info("Old customer data cleanup initiated (placeholder for complex logic).")

        session.commit()
        logging.info("Old data cleanup completed.")
    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred during data cleanup: {e}")
    finally:
        session.close()

def generate_duplicate_data_file():
    """
    Generates a file containing identified duplicate customer records.
    (FR32)
    """
    session = _get_db_session()
    output = io.StringIO()
    writer = csv.writer(output)
    header = ['customer_id', 'mobile_number', 'pan_number', 'aadhaar_number', 'duplicate_of_customer_id', 'reason']
    writer.writerow(header)

    try:
        # This would query the results of the deduplication process,
        # assuming duplicates are marked or stored in a specific way.
        # For mock, return empty.
        logging.info("Duplicate data file generated (mock).")
        return output.getvalue()
    except Exception as e:
        logging.error(f"Error generating duplicate data file: {e}")
        return None
    finally:
        session.close()

def generate_unique_data_file():
    """
    Generates a file containing unique customer records after deduplication.
    (FR33)
    """
    session = _get_db_session()
    output = io.StringIO()
    writer = csv.writer(output)
    header = ['customer_id', 'mobile_number', 'pan_number', 'aadhaar_number', 'segment', 'dnd_flag']
    writer.writerow(header)

    try:
        # Query unique customers (e.g., those not marked as duplicates).
        # For mock, return empty.
        logging.info("Unique data file generated (mock).")
        return output.getvalue()
    except Exception as e:
        logging.error(f"Error generating unique data file: {e}")
        return None
    finally:
        session.close()

def generate_error_excel_file(log_id: str = None):
    """
    Generates an Excel file (mocked as CSV) detailing errors from data ingestion processes.
    (FR34)
    Note: Generating actual Excel (.xlsx) files requires a library like `openpyxl`.
    This implementation returns CSV content for simplicity.
    """
    session = _get_db_session()
    output = io.StringIO()
    writer = csv.writer(output)
    header = ['log_id', 'file_name', 'upload_timestamp', 'status', 'error_description']
    writer.writerow(header)

    try:
        # Retrieve error logs from the IngestionLog table
        if log_id:
            error_logs = session.query(IngestionLog).filter_by(log_id=log_id, status='FAILED').all()
        else:
            # If no specific log_id, fetch recent errors (e.g., last 24 hours)
            recent_errors_threshold = datetime.now() - timedelta(days=1)
            error_logs = session.query(IngestionLog).filter(
                IngestionLog.status == 'FAILED',
                IngestionLog.upload_timestamp >= recent_errors_threshold
            ).order_by(IngestionLog.upload_timestamp.desc()).all()

        for log in error_logs:
            writer.writerow([log.log_id, log.file_name, log.upload_timestamp.isoformat(), log.status, log.error_description])

        logging.info(f"Error file generated for log_id: {log_id if log_id else 'recent errors'} (mock CSV, intended Excel).")
        return output.getvalue()
    except Exception as e:
        logging.error(f"Error generating error file: {e}")
        return None
    finally:
        session.close()