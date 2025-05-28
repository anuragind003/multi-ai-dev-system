from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_, and_
from sqlalchemy.orm.exc import StaleDataError

# Assuming db and models are defined in app.extensions and app.models respectively
# This is a common Flask project structure.
# In a real application, ensure these imports are resolvable.
try:
    from app.extensions import db
    from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog
except ImportError:
    # This block provides mock objects for standalone execution/testing
    # if the Flask app context and full project structure are not available.
    # In a production Flask application, these imports should work directly.
    print("WARNING: Could not import app.extensions or app.models. Using mock objects for standalone execution.")
    class MockDB:
        def session(self):
            return self
        def delete(self, obj):
            print(f"MOCK DB: Deleting {obj.__class__.__name__} with ID {getattr(obj, 'id', 'N/A')}")
        def commit(self):
            print("MOCK DB: Committing changes.")
        def rollback(self):
            print("MOCK DB: Rolling back changes.")
        def query(self, model):
            return MockQuery(model)
        def remove(self):
            print("MOCK DB: Session removed.")

    class MockQuery:
        def __init__(self, model):
            self.model = model
            self._filters = []
        def filter(self, *args):
            self._filters.extend(args)
            return self
        def delete(self, synchronize_session=False):
            print(f"MOCK DB: Deleting from {self.model.__name__} with filters: {self._filters}")
            return 1 # Simulate rows affected
        def all(self):
            return [] # Simulate no results

    db = MockDB()

    # Mock models for standalone execution
    class MockModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def __repr__(self):
            return f"<{self.__class__.__name__} id={getattr(self, 'id', 'N/A')}>"

    class Customer(MockModel):
        __tablename__ = 'customers'
        id = None # Placeholder for primary key

    class Offer(MockModel):
        __tablename__ = 'offers'
        id = None
        created_at = None # Assuming this column exists for retention logic

    class CustomerEvent(MockModel):
        __tablename__ = 'customer_events'
        id = None
        event_timestamp = None # Assuming this column exists for retention logic

    class Campaign(MockModel):
        __tablename__ = 'campaigns'
        id = None
        created_at = None # Assuming this column exists for retention logic

    class DataIngestionLog(MockModel):
        __tablename__ = 'data_ingestion_logs'
        id = None
        upload_timestamp = None # Assuming this column exists for retention logic


def cleanup_old_data():
    """
    Task to enforce data retention policies:
    - Retain offer history for 6 months (FR18, NFR3).
    - Retain all other data in CDP for 3 months before deletion (FR24, NFR4).
    """
    # Use current_app.logger for logging within a Flask application context.
    # Fallback to print if not in an app context (e.g., for standalone testing).
    logger = current_app.logger if current_app else print

    logger.info("Starting data cleanup task...")
    try:
        # Calculate cutoff dates based on UTC time
        # Using 30 days per month for approximation as per RAG context.
        # For precise calendar month calculations, consider dateutil or more complex logic.
        three_months_ago = datetime.utcnow() - timedelta(days=3 * 30)
        six_months_ago = datetime.utcnow() - timedelta(days=6 * 30)

        session = db.session

        # 1. Delete Offer records older than 6 months (FR18, NFR3)
        # Deletes offers where the creation timestamp is before the 6-month cutoff.
        offers_deleted = session.query(Offer).filter(Offer.created_at < six_months_ago).delete(synchronize_session=False)
        logger.info(f"Deleted {offers_deleted} offer records older than 6 months.")

        # 2. Delete CustomerEvent records older than 3 months (FR24, NFR4)
        # Deletes customer events where the event timestamp is before the 3-month cutoff.
        customer_events_deleted = session.query(CustomerEvent).filter(CustomerEvent.event_timestamp < three_months_ago).delete(synchronize_session=False)
        logger.info(f"Deleted {customer_events_deleted} customer event records older than 3 months.")

        # 3. Delete Campaign records older than 3 months (FR24, NFR4)
        # Deletes campaign records where the creation timestamp is before the 3-month cutoff.
        campaigns_deleted = session.query(Campaign).filter(Campaign.created_at < three_months_ago).delete(synchronize_session=False)
        logger.info(f"Deleted {campaigns_deleted} campaign records older than 3 months.")

        # 4. Delete DataIngestionLog records older than 3 months (FR24, NFR4)
        # Deletes data ingestion log records where the upload timestamp is before the 3-month cutoff.
        data_logs_deleted = session.query(DataIngestionLog).filter(DataIngestionLog.upload_timestamp < three_months_ago).delete(synchronize_session=False)
        logger.info(f"Deleted {data_logs_deleted} data ingestion log records older than 3 months.")

        # 5. Customer table deletion:
        # The Customer table represents the core "single profile view" (FR2).
        # Deleting Customer records requires careful consideration to avoid breaking
        # foreign key constraints with Offers (6-month retention) or CustomerEvents (3-month retention).
        # The BRD states "maintain all data in LTFS Offer CDP for previous 3 months before deletion" (FR24),
        # but deleting core customer profiles based on a simple 3-month rule could lead to data loss
        # if associated offers are still within their 6-month retention period.
        # For an MVP, and given the ambiguity, it is safer to *not* automatically delete core Customer profiles
        # unless they are explicitly defined as "orphaned" or "inactive" with clear, robust rules
        # that account for all related data retention policies.
        # Therefore, Customer records are NOT deleted in this general cleanup task.
        # If specific rules for deleting truly inactive/orphaned customers are provided,
        # this section can be updated.
        logger.info("Customer records are not automatically deleted by this task due to complex retention dependencies and the need to maintain a single customer profile view.")

        session.commit()
        logger.info("Data cleanup task completed successfully.")

    except StaleDataError as e:
        # This can occur in highly concurrent environments if data is modified
        # between query and delete operations. For bulk deletes, it's less common.
        logger.error(f"StaleDataError during cleanup: {e}. Rolling back transaction.")
        db.session.rollback()
    except Exception as e:
        logger.error(f"An unexpected error occurred during data cleanup: {e}")
        db.session.rollback()
    finally:
        # Ensure the session is closed/removed from the pool after each operation
        db.session.remove()

def run_maintenance_tasks():
    """
    Orchestrates all scheduled maintenance tasks.
    This function can be called by a scheduler (e.g., Celery beat, cron job)
    within the Flask application context.
    """
    cleanup_old_data()

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
    #     run_maintenance_tasks()

    # For direct execution without a full Flask app context (will use mock objects if imports fail):
    run_maintenance_tasks()