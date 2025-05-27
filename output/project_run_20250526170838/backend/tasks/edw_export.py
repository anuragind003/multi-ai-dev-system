import os
import csv
import logging
from datetime import datetime, date
from sqlalchemy import create_engine, Column, String, Boolean, Date, DateTime, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# --- Configuration ---
# In a production environment, DATABASE_URL and EDW_EXPORT_DIR would typically
# be loaded from a Flask app's config, environment variables, or a dedicated
# configuration management system.
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')
EDW_EXPORT_DIR = os.getenv('EDW_EXPORT_DIR', '/tmp/edw_exports')

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Setup ---
Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# --- SQLAlchemy Models ---
# These models reflect the database schema provided in the system design.
# For a standalone task, defining them here is acceptable. In a larger
# Flask application, these would typically reside in a shared 'models.py' file.

class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(Text, primary_key=True)
    mobile_number = Column(Text, unique=True)
    pan_number = Column(Text, unique=True)
    aadhaar_number = Column(Text, unique=True)
    ucid_number = Column(Text, unique=True)
    loan_application_number = Column(Text, unique=True)
    dnd_flag = Column(Boolean, default=False)
    segment = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class Offer(Base):
    __tablename__ = 'offers'
    offer_id = Column(Text, primary_key=True)
    customer_id = Column(Text)
    offer_type = Column(Text)
    offer_status = Column(Text)
    propensity = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    channel = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class Event(Base):
    __tablename__ = 'events'
    event_id = Column(Text, primary_key=True)
    customer_id = Column(Text)
    event_type = Column(Text)
    event_source = Column(Text)
    event_timestamp = Column(DateTime)
    event_details = Column(JSONB)
    created_at = Column(DateTime)

class CampaignMetric(Base):
    __tablename__ = 'campaign_metrics'
    metric_id = Column(Text, primary_key=True)
    campaign_unique_id = Column(Text, unique=True)
    campaign_name = Column(Text)
    campaign_date = Column(Date)
    attempted_count = Column(Integer)
    sent_success_count = Column(Integer)
    failed_count = Column(Integer)
    conversion_rate = Column(Numeric(5, 2))
    created_at = Column(DateTime)

# --- Export Helper Function ---

def export_table_to_csv(session, model, filename, output_dir):
    """
    Exports data from a given SQLAlchemy model to a CSV file.
    Handles conversion of datetime, date, and JSONB types for CSV compatibility.
    """
    filepath = os.path.join(output_dir, filename)
    try:
        records = session.query(model).all()
        if not records:
            logger.info(f"No records found for {model.__tablename__}. "
                        f"Skipping export to {filename}.")
            return

        # Get column names from the model's mapped attributes
        columns = [c.name for c in model.__table__.columns]

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)  # Write header row
            for record in records:
                row = []
                for col in columns:
                    value = getattr(record, col)
                    # Convert specific types to string for CSV
                    if isinstance(value, (datetime, date)):
                        row.append(value.isoformat())
                    elif isinstance(value, dict):
                        row.append(str(value))  # Convert dict to string
                    else:
                        row.append(value)
                writer.writerow(row)
        logger.info(f"Successfully exported {len(records)} records from "
                    f"{model.__tablename__} to {filepath}")
    except Exception as e:
        logger.error(f"Error exporting {model.__tablename__} to CSV: {e}")
        raise  # Re-raise to indicate failure

# --- Main Export Function ---

def export_data_to_edw(output_dir=EDW_EXPORT_DIR):
    """
    Exports all relevant CDP data (customers, offers, events, campaign metrics)
    to CSV files for EDW consumption. This function is intended to be run
    as a daily scheduled task (FR27).
    """
    logger.info(f"Starting EDW data export to directory: {output_dir}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created export directory: {output_dir}")

    session = Session()
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export Customers data
        customer_filename = f"cdp_customers_{timestamp}.csv"
        export_table_to_csv(session, Customer, customer_filename, output_dir)

        # Export Offers data
        offer_filename = f"cdp_offers_{timestamp}.csv"
        export_table_to_csv(session, Offer, offer_filename, output_dir)

        # Export Events data
        event_filename = f"cdp_events_{timestamp}.csv"
        export_table_to_csv(session, Event, event_filename, output_dir)

        # Export Campaign Metrics data
        campaign_metrics_filename = f"cdp_campaign_metrics_{timestamp}.csv"
        export_table_to_csv(session, CampaignMetric,
                            campaign_metrics_filename, output_dir)

        logger.info("EDW data export completed successfully.")
    except SQLAlchemyError as e:
        session.rollback()
        logger.critical(f"Database error during EDW export: {e}")
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred during EDW export: {e}")
        raise
    finally:
        session.close()

# --- Main Execution Block ---
if __name__ == "__main__":
    # This block allows the script to be run directly, e.g., via cron job
    # or a task scheduler.
    # Example usage: python backend/tasks/edw_export.py
    try:
        export_data_to_edw()
    except Exception as e:
        logger.error(f"EDW export failed: {e}")
        # Exit with a non-zero status code to indicate failure in a script context
        exit(1)