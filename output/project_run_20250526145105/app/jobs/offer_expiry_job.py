import logging
from datetime import date, datetime, timezone
from contextlib import contextmanager
import uuid

from sqlalchemy import create_engine, Column, String, Date, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    DATABASE_URL: Connection string for the PostgreSQL database.
    """
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/cdp_db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# --- Database Setup ---
DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Models ---
class Offer(Base):
    """
    SQLAlchemy model for the 'offers' table.
    Reflects the database schema provided in system_design.
    """
    __tablename__ = "offers"

    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    offer_type = Column(String(50))
    offer_status = Column(String(50), default="Active") # e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'
    product_type = Column(String(50))
    offer_details = Column(JSONB) # Flexible storage for offer specific data
    offer_start_date = Column(Date)
    offer_end_date = Column(Date)
    is_journey_started = Column(Boolean, default=False)
    loan_application_id = Column(String(50)) # Populated if journey started
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            f"<Offer(offer_id={self.offer_id}, status='{self.offer_status}', "
            f"end_date={self.offer_end_date}, is_journey_started={self.is_journey_started})>"
        )

# Helper to get a database session using a context manager
@contextmanager
def get_db_session_context():
    """
    Provides a SQLAlchemy session for database operations.
    Ensures the session is closed after use, even if errors occur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Offer Expiry Logic ---
def mark_expired_offers():
    """
    Identifies and marks offers as 'Expired' based on specific business logic.

    Adheres to:
    - FR51: "The system shall mark offers as expired based on offer end dates
            for non-journey started customers."

    Note on FR53:
    - FR53: "The system shall mark offers as expired within the offers data if
            the LAN validity post loan application journey start date is over."
    This logic is not implemented here due to ambiguity in the "LAN validity"
    period (as noted in BRD Question 9) and the lack of a direct field in the
    'offers' table to store this specific validity period. It is assumed that
    this might be handled by a separate process or trigger from the LOS system,
    or requires further clarification on data points.
    """
    logger.info("Starting offer expiry job...")
    current_date = date.today() # Get today's date for comparison

    try:
        with get_db_session_context() as db_session:
            # Query for offers that meet the expiry criteria:
            # 1. Offer status is 'Active'
            # 2. Loan application journey has NOT started (is_journey_started = False)
            # 3. Offer end date is today or in the past
            offers_to_expire = db_session.query(Offer).filter(
                Offer.offer_status == "Active",
                Offer.is_journey_started == False,
                Offer.offer_end_date <= current_date
            ).all()

            if not offers_to_expire:
                logger.info("No active, non-journey started offers found for expiry today.")
                return

            logger.info(f"Found {len(offers_to_expire)} offers to expire.")
            updated_count = 0
            for offer in offers_to_expire:
                old_status = offer.offer_status
                offer.offer_status = "Expired"
                # The 'updated_at' column will be automatically updated by SQLAlchemy's
                # 'onupdate=func.now()' configuration when the session is committed.
                updated_count += 1
                logger.debug(f"Offer {offer.offer_id} status changed from '{old_status}' to 'Expired'.")

            db_session.commit()
            logger.info(f"Successfully marked {updated_count} offers as 'Expired'.")

    except Exception as e:
        # Log the error and re-raise or handle as appropriate for a job.
        # The context manager handles session closing, but explicit rollback
        # might be desired if partial updates are not acceptable.
        logger.error(f"Error during offer expiry job: {e}", exc_info=True)
        # In a real scenario, you might want to send an alert or retry.

# --- Main execution block ---
if __name__ == "__main__":
    # This block allows the script to be run directly for testing or as a cron job.
    # In a full FastAPI application, this function would typically be called
    # by a background task scheduler (e.g., APScheduler, Celery Beat)
    # configured within the main FastAPI application.
    logger.info("Running offer_expiry_job.py as a standalone script.")
    mark_expired_offers()
    logger.info("Offer expiry job finished.")