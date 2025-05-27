import os
import pandas as pd
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_engine():
    """Returns a SQLAlchemy engine."""
    return create_engine(settings.DATABASE_URL)

def run_daily_edw_export():
    """
    Performs the daily export of CDP data to EDW.
    This job extracts customer, offer, and campaign event data,
    joins them, and exports to a CSV file.
    """
    logger.info("Starting daily EDW export job...")

    engine = get_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Define the export directory and filename
        export_dir = settings.EDW_EXPORT_PATH
        os.makedirs(export_dir, exist_ok=True)
        export_date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"cdp_edw_export_{export_date_str}.csv"
        export_path = os.path.join(export_dir, file_name)

        logger.info(f"Exporting data to: {export_path}")

        # SQL query to join customers, offers, and campaign events.
        # This query aims to provide a comprehensive, flattened view for EDW.
        # It will produce multiple rows for a customer if they have multiple offers
        # or multiple campaign events associated with an offer/customer.
        query = text("""
            SELECT
                c.customer_id,
                c.mobile_number,
                c.pan_number,
                c.aadhaar_ref_number,
                c.ucid_number,
                c.previous_loan_app_number,
                c.customer_attributes,
                c.customer_segments,
                c.propensity_flag,
                c.dnd_status,
                c.created_at AS customer_created_at,
                c.updated_at AS customer_updated_at,
                o.offer_id,
                o.offer_type,
                o.offer_status,
                o.product_type,
                o.offer_details,
                o.offer_start_date,
                o.offer_end_date,
                o.is_journey_started,
                o.loan_application_id,
                o.created_at AS offer_created_at,
                o.updated_at AS offer_updated_at,
                ce.event_id,
                ce.event_source,
                ce.event_type,
                ce.event_details,
                ce.event_timestamp
            FROM
                customers c
            LEFT JOIN
                offers o ON c.customer_id = o.customer_id
            LEFT JOIN
                campaign_events ce ON c.customer_id = ce.customer_id AND (o.offer_id IS NULL OR ce.offer_id = o.offer_id)
            ORDER BY
                c.customer_id, o.offer_id, ce.event_timestamp;
        """)

        # Fetch data using pandas read_sql for direct DataFrame creation
        df = pd.read_sql(query, db.connection())

        # Handle JSONB and array columns for CSV export
        # Convert JSONB columns to string representation
        if 'customer_attributes' in df.columns:
            df['customer_attributes'] = df['customer_attributes'].apply(lambda x: str(x) if x else None)
        if 'offer_details' in df.columns:
            df['offer_details'] = df['offer_details'].apply(lambda x: str(x) if x else None)
        if 'event_details' in df.columns:
            df['event_details'] = df['event_details'].apply(lambda x: str(x) if x else None)
        
        # Convert PostgreSQL array (TEXT[]) to comma-separated string
        if 'customer_segments' in df.columns:
            df['customer_segments'] = df['customer_segments'].apply(lambda x: ','.join(x) if isinstance(x, list) else None)

        # Export to CSV
        df.to_csv(export_path, index=False)

        logger.info(f"Daily EDW export completed successfully. Data saved to {export_path}")

    except Exception as e:
        logger.error(f"Error during daily EDW export: {e}", exc_info=True)
        raise # Re-raise the exception to indicate job failure
    finally:
        db.close()
        logger.info("Database session closed.")

if __name__ == "__main__":
    # This block allows running the job directly for testing/manual execution.
    # In a production environment, this would typically be triggered by a scheduler
    # like cron, Airflow, or Celery Beat.
    # Ensure environment variables or a .env file are set up for
    # settings.DATABASE_URL and settings.EDW_EXPORT_PATH before running.
    try:
        run_daily_edw_export()
    except Exception as e:
        logger.critical(f"Daily EDW export job failed critically: {e}")