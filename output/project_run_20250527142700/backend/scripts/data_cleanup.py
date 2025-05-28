import os
import logging
from datetime import datetime, timedelta

from sqlalchemy import create_engine, Column, String, Boolean, DateTime, UUID, Text, Integer, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cdp_db")

# Define SQLAlchemy Base
Base = declarative_base()

# Define database models (should be consistent with your application's models)
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
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

class Offer(Base):
    __tablename__ = 'offers'
    offer_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False) # No direct foreign key constraint here to allow deletion of offers without cascade deleting customers
    source_offer_id = Column(String(100))
    offer_type = Column(String(50))
    offer_status = Column(String(50)) # 'Active', 'Inactive', 'Expired'
    propensity = Column(String(50))
    loan_application_number = Column(String(100))
    valid_until = Column(DateTime(timezone=True))
    source_system = Column(String(50))
    channel = Column(String(50))
    is_duplicate = Column(Boolean, default=False)
    original_offer_id = Column(UUID(as_uuid=True)) # No direct foreign key constraint
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

class OfferHistory(Base):
    __tablename__ = 'offer_history'
    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), nullable=False) # No direct foreign key constraint
    status_change_date = Column(DateTime(timezone=True), default=datetime.now)
    old_status = Column(String(50))
    new_status = Column(String(50))
    change_reason = Column(Text)

class Event(Base):
    __tablename__ = 'events'
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True)) # No direct foreign key constraint
    offer_id = Column(UUID(as_uuid=True)) # No direct foreign key constraint
    event_type = Column(String(100), nullable=False)
    event_timestamp = Column(DateTime(timezone=True), default=datetime.now)
    source_system = Column(String(50), nullable=False)
    event_details = Column(JSONB)

class Campaign(Base):
    __tablename__ = 'campaigns'
    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_name = Column(String(255), nullable=False)
    campaign_date = Column(DateTime, nullable=False)
    campaign_unique_identifier = Column(String(100), unique=True, nullable=False)
    attempted_count = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    success_rate = Column(Numeric(5,2), default=0.0)
    conversion_rate = Column(Numeric(5,2), default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


def get_db_session():
    """Establishes a database connection and returns a session."""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        raise

def clean_offer_history(session):
    """
    Deletes offer history records older than 6 months.
    (NFR10: Offer history shall be maintained for 6 months.)
    """
    cutoff_date = datetime.now() - timedelta(days=6 * 30) # Approximately 6 months
    logging.info(f"Cleaning offer_history older than {cutoff_date.isoformat()}")
    try:
        deleted_count = session.query(OfferHistory).filter(
            OfferHistory.status_change_date < cutoff_date
        ).delete(synchronize_session=False)
        session.commit()
        logging.info(f"Successfully deleted {deleted_count} offer history records.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error cleaning offer history: {e}")

def clean_stale_offers(session):
    """
    Deletes offers that are 'Expired' or 'Inactive' and older than 3 months.
    (FR29, NFR11: All data in CDP shall be maintained for previous 3 months before deletion from CDP.)
    This applies to stale offers.
    """
    cutoff_date = datetime.now() - timedelta(days=3 * 30) # Approximately 3 months
    logging.info(f"Cleaning stale offers (Expired/Inactive) older than {cutoff_date.isoformat()}")
    try:
        deleted_count = session.query(Offer).filter(
            Offer.offer_status.in_(['Expired', 'Inactive']),
            Offer.updated_at < cutoff_date # Use updated_at to reflect when it became stale
        ).delete(synchronize_session=False)
        session.commit()
        logging.info(f"Successfully deleted {deleted_count} stale offer records.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error cleaning stale offers: {e}")

def clean_old_events(session):
    """
    Deletes event records older than 3 months.
    (FR29, NFR11: All data in CDP shall be maintained for previous 3 months before deletion from CDP.)
    """
    cutoff_date = datetime.now() - timedelta(days=3 * 30) # Approximately 3 months
    logging.info(f"Cleaning event records older than {cutoff_date.isoformat()}")
    try:
        deleted_count = session.query(Event).filter(
            Event.event_timestamp < cutoff_date
        ).delete(synchronize_session=False)
        session.commit()
        logging.info(f"Successfully deleted {deleted_count} event records.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error cleaning old events: {e}")

def run_data_cleanup():
    """
    Main function to orchestrate the data cleanup process.
    """
    logging.info("Starting data cleanup script...")
    session = None
    try:
        session = get_db_session()
        
        clean_offer_history(session)
        clean_stale_offers(session)
        clean_old_events(session)

        logging.info("Data cleanup script completed successfully.")
    except Exception as e:
        logging.critical(f"Data cleanup script failed: {e}")
    finally:
        if session:
            session.close()
            logging.info("Database session closed.")

if __name__ == "__main__":
    run_data_cleanup()