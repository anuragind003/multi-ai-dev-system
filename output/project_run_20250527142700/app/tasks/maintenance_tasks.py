from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_, and_, not_, exists, cast, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased

# Assuming db and models are defined in app.extensions and app.models respectively
# This is a common Flask project structure.
try:
    from app.extensions import db
    from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog
except ImportError:
    # This block is for local testing/demonstration purposes when app context is not fully set up.
    # In a real Flask application, these imports would typically succeed.
    print("WARNING: Could not import app.extensions or app.models. Using mock objects for standalone execution.")

    class MockModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def __repr__(self):
            return f"<{self.__class__.__name__} Mock>"
        @classmethod
        def __tablename__(cls):
            return cls.__name__.lower() + 's'
        @classmethod
        def query(cls):
            return MockDB().query(cls)

    class Customer(MockModel):
        customer_id = None
        created_at = None
    class Offer(MockModel):
        offer_id = None
        customer_id = None
        offer_status = None
        loan_application_number = None
        offer_end_date = None
        created_at = None
        updated_at = None
    class CustomerEvent(MockModel):
        event_id = None
        customer_id = None
        event_timestamp = None
        loan_application_number = None
        event_type = None
        event_details = None
    class Campaign(MockModel):
        campaign_id = None
        created_at = None
    class DataIngestionLog(MockModel):
        log_id = None
        upload_timestamp = None

    class MockLogger:
        def info(self, msg):
            print(f"INFO: {msg}")
        def error(self, msg):
            print(f"ERROR: {msg}")

    class MockApp:
        def __init__(self):
            self.logger = MockLogger()

    class MockQuery:
        def __init__(self, model_cls=None):
            self.model_cls = model_cls
            self._filters = []
            self._joins = []
            self._group_by = []
            self._distinct = False

        def filter(self, *args):
            self._filters.extend(args)
            return self

        def join(self, *args):
            self._joins.extend(args)
            return self

        def group_by(self, *args):
            self._group_by.extend(args)
            return self

        def distinct(self):
            self._distinct = True
            return self

        def delete(self, synchronize_session=False):
            print(f"Mock DB: Deleting {self.model_cls.__name__} records. Sync: {synchronize_session}")
            return 0 # Return 0 for mock

        def update(self, values, synchronize_session=False):
            print(f"Mock DB: Updating {self.model_cls.__name__} records with {values}. Sync: {synchronize_session}")
            return 0 # Return 0 for mock

        def all(self):
            print(f"Mock DB: Executing .all() for {self.model_cls.__name__}")
            # Return mock objects for iteration if needed for specific tests
            if self.model_cls == Offer:
                # Simulate an offer that would be expired for testing update_offer_expiry
                return [Offer(offer_id='mock_offer_1', offer_status='Active', loan_application_number='mock_lan_1')]
            return []

        def subquery(self):
            print("Mock DB: Creating subquery")
            return self # Return self to allow chaining

        def label(self, name):
            print(f"Mock DB: Labeling as {name}")
            return self # Return self to allow chaining

        def astext(self):
            print("Mock DB: Calling .astext()")
            return self # Allow chaining to .in_()

        def in_(self, values):
            print(f"Mock DB: Calling .in_({values})")
            return True # Mock condition

        def is_(self, val):
            print(f"Mock DB: is_({val})")
            return True # Mock condition

        def isnot(self, val):
            print(f"Mock DB: isnot({val})")
            return True # Mock condition

        def __getitem__(self, key):
            print(f"Mock DB: Accessing JSONB key '{key}'")
            return self # Allow chaining for JSONB access

        def __getattr__(self, name):
            # Mock column access for subquery.c.column_name or model.column_name
            if name in ['customer_id', 'loan_application_number', 'max_timestamp', 'offer_id', 'event_timestamp', 'created_at', 'updated_at', 'offer_end_date', 'offer_status', 'event_type', 'event_details', 'c']:
                return self
            raise AttributeError(f"MockQuery has no attribute {name}")

    class MockDB:
        def __init__(self):
            self.session = self

        def query(self, model_cls):
            print(f"Mock DB: Querying {model_cls.__name__}")
            return MockQuery(model_cls)

        def commit(self):
            print("Mock DB: Committing transaction.")

        def rollback(self):
            print("Mock DB: Rolling back transaction.")

        def add(self, obj):
            print(f"Mock DB: Adding/updating object {obj.__class__.__name__}")

        def func(self):
            class MockFunc:
                def max(self, col):
                    print(f"Mock DB Func: max({col})")
                    return MockQuery() # Return a query object for chaining
            return MockFunc()

        def cast(self, col, type_):
            print(f"Mock DB: Casting {col} to {type_}")
            return MockQuery() # Return a query object for chaining

        @property
        def String(self):
            print("Mock DB: Accessing String type")
            return "MockStringType" # This will be used as `type_` in cast

    db = MockDB()
    current_app = MockApp()


def cleanup_old_data():
    """
    Task to enforce data retention policies as per BRD:
    - Retain offer history for 6 months (FR18, NFR3).
    - Retain all other data in CDP for 3 months before deletion (FR24, NFR4).
    - Customer records are deleted only if they have no associated offers within 6 months
      and no associated events within 3 months, and the customer record itself is older than 3 months.
    """
    logger = current_app.logger
    logger.info("Starting data cleanup task...")

    try:
        now = datetime.utcnow()
        # Using 30 days per month for approximation, adjust if exact calendar months are needed
        three_months_ago = now - timedelta(days=3 * 30)
        six_months_ago = now - timedelta(days=6 * 30)

        # 1. Delete old Offers (older than 6 months)
        # Offers are retained for 6 months based on their updated_at or created_at
        offers_deleted = db.session.query(Offer).filter(
            or_(
                Offer.updated_at < six_months_ago,
                Offer.created_at < six_months_ago # Ensure offers never updated are also considered
            )
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {offers_deleted} old offers.")

        # 2. Delete old Customer Events (older than 3 months)
        events_deleted = db.session.query(CustomerEvent).filter(
            CustomerEvent.event_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {events_deleted} old customer events.")

        # 3. Delete old Campaigns (older than 3 months)
        campaigns_deleted = db.session.query(Campaign).filter(
            Campaign.created_at < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {campaigns_deleted} old campaigns.")

        # 4. Delete old Data Ingestion Logs (older than 3 months)
        logs_deleted = db.session.query(DataIngestionLog).filter(
            DataIngestionLog.upload_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {logs_deleted} old data ingestion logs.")

        # 5. Delete Customers who have no recent associated data and are themselves old
        # A customer is considered 'recent' if they have:
        # - an offer updated/created in the last 6 months
        # - an event in the last 3 months
        # - or the customer record itself was created in the last 3 months

        # Subquery for customers with recent offers
        recent_offers_subquery = db.session.query(Offer.customer_id).filter(
            or_(
                Offer.updated_at >= six_months_ago,
                Offer.created_at >= six_months_ago
            )
        ).distinct().subquery()

        # Subquery for customers with recent events
        recent_events_subquery = db.session.query(CustomerEvent.customer_id).filter(
            CustomerEvent.event_timestamp >= three_months_ago
        ).distinct().subquery()

        # Find customers to delete:
        # - created more than 3 months ago
        # - NOT in recent_offers_subquery
        # - NOT in recent_events_subquery
        customers_to_delete_ids = db.session.query(Customer.customer_id).filter(
            Customer.created_at < three_months_ago,
            not_(Customer.customer_id.in_(recent_offers_subquery)),
            not_(Customer.customer_id.in_(recent_events_subquery))
        ).all()

        customer_ids_to_delete = [c.customer_id for c in customers_to_delete_ids]

        if customer_ids_to_delete:
            customers_deleted = db.session.query(Customer).filter(
                Customer.customer_id.in_(customer_ids_to_delete)
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {customers_deleted} old customer records.")
        else:
            logger.info("No old customer records to delete.")

        db.session.commit()
        logger.info("Data cleanup task completed successfully.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error during data cleanup task: {e}")
        raise # Re-raise to indicate task failure if run by a scheduler

def update_offer_expiry():
    """
    Task to update offer statuses based on expiry logic (FR13, FR37, FR38).
    - For non-journey started offers: Expire if offer_end_date is past.
    - For journey started offers: Expire if LAN validity is over (e.g., application rejected/expired).
    """
    logger = current_app.logger
    logger.info("Starting offer expiry update task...")

    try:
        now_date = datetime.utcnow().date() # Compare dates only

        # Case 1: Non-journey started offers (loan_application_number is NULL)
        # Mark as 'Expired' if offer_end_date is in the past
        offers_non_journey_expired = db.session.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.loan_application_number.is_(None),
            Offer.offer_end_date < now_date
        ).update({Offer.offer_status: 'Expired', Offer.updated_at: datetime.utcnow()}, synchronize_session=False)
        logger.info(f"Expired {offers_non_journey_expired} non-journey started offers.")

        # Case 2: Journey started offers (loan_application_number is NOT NULL)
        # Mark as 'Expired' if the associated loan application is rejected or expired.
        # This requires checking the latest status from customer_events for the specific LAN.

        # Define terminal negative application stages from event_details JSONB
        # Assuming event_type is 'APP_STAGE_UPDATE' or similar, and actual stage is in event_details->>'stage'
        terminal_negative_stages_in_details = ['REJECTED', 'EXPIRED', 'WITHDRAWN', 'CANCELLED']

        # Step 1: Find the latest timestamp for each loan_application_number
        latest_ts_per_lan = db.session.query(
            CustomerEvent.loan_application_number,
            db.func.max(CustomerEvent.event_timestamp).label('max_timestamp')
        ).filter(
            CustomerEvent.loan_application_number.isnot(None)
        ).group_by(CustomerEvent.loan_application_number).subquery()

        # Step 2: Join back to CustomerEvent to get the full latest event record
        # and filter by terminal stages in event_details
        latest_terminal_events_lan_ids = db.session.query(CustomerEvent.loan_application_number).join(
            latest_ts_per_lan,
            and_(
                CustomerEvent.loan_application_number == latest_ts_per_lan.c.loan_application_number,
                CustomerEvent.event_timestamp == latest_ts_per_lan.c.max_timestamp
            )
        ).filter(
            # Check if the event_details->>'stage' is in the terminal negative list
            cast(CustomerEvent.event_details['stage'], String).astext.in_(terminal_negative_stages_in_details)
        ).distinct().subquery()

        # Step 3: Update offers whose loan_application_number is in the list of LANs with latest terminal events
        offers_journey_expired_count = db.session.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.loan_application_number.isnot(None),
            Offer.loan_application_number.in_(latest_terminal_events_lan_ids)
        ).update({Offer.offer_status: 'Expired', Offer.updated_at: datetime.utcnow()}, synchronize_session=False)

        logger.info(f"Expired {offers_journey_expired_count} journey-started offers based on terminal application status.")

        db.session.commit()
        logger.info("Offer expiry update task completed successfully.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error during offer expiry update task: {e}")
        raise # Re-raise to indicate task failure if run by a scheduler

if __name__ == '__main__':
    # This block is for local testing/demonstration purposes.
    # In a real Flask application, these tasks would typically be run via
    # a Flask CLI command, a Celery worker, or a cron job, ensuring the
    # Flask app context and database are properly initialized.
    print("Running maintenance tasks (this might require a Flask app context and DB setup).")
    print("If you see 'WARNING: Could not import app.extensions or app.models. Using mock objects.',")
    print("this script is running in standalone mode with mocked DB interactions.")
    print("For full functionality, run within a Flask application context.")

    # To run this with a full Flask app context (e.g., for testing):
    # from app import create_app # Assuming create_app() exists in your main app file
    # app = create_app()
    # with app.app_context():
    #     cleanup_old_data()
    #     update_offer_expiry()

    # For demonstration purposes without a full app context:
    # These calls will use the mocked db and current_app
    cleanup_old_data()
    update_offer_expiry()