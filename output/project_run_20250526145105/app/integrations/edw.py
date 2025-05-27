import os
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid # Required for checking UUID type

from app.database import get_db
from app.models import models # Assuming models are defined here, e.g., models.Customer, models.Offer etc.

# Configuration for EDW export
# The directory where EDW export files will be saved.
# Defaults to 'edw_exports' if not set in environment variables.
EDW_EXPORT_DIR = os.getenv("EDW_EXPORT_DIR", "edw_exports")

# Ensure the export directory exists
os.makedirs(EDW_EXPORT_DIR, exist_ok=True)

def _fetch_data_to_dataframe(db: Session, model, date_column: str = None, days_back: int = None) -> pd.DataFrame:
    """
    Fetches data from a given SQLAlchemy model and returns it as a pandas DataFrame.
    Optionally filters records by a date column to include only data within the last 'days_back' days.

    Args:
        db (Session): The SQLAlchemy database session.
        model: The SQLAlchemy model class (e.g., models.Customer, models.Offer).
        date_column (str, optional): The name of the datetime column to filter by.
                                     Defaults to None, meaning no date filtering.
        days_back (int, optional): The number of days back from the current date to include records.
                                   Only applicable if `date_column` is provided. Defaults to None.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the fetched data. Returns an empty DataFrame
                      if no records are found or if an error occurs during fetching.
    """
    query = db.query(model)

    if date_column and days_back is not None:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        # Using text() for dynamic column name in filter, which is common for flexible queries.
        # For production, consider using getattr(model, date_column) if column names are fixed.
        query = query.filter(text(f"{date_column} >= :cutoff_date")).params(cutoff_date=cutoff_date)

    records = query.all()
    if not records:
        return pd.DataFrame()

    # Convert SQLAlchemy objects to dictionaries for DataFrame creation
    data = []
    for record in records:
        record_dict = {}
        for column in record.__table__.columns:
            value = getattr(record, column.name)
            # Convert UUID objects to string for better CSV compatibility
            if isinstance(value, uuid.UUID):
                record_dict[column.name] = str(value)
            # Convert dictionary (JSONB) values to string representation for CSV compatibility
            elif isinstance(value, dict):
                record_dict[column.name] = str(value)
            else:
                record_dict[column.name] = value
        data.append(record_dict)

    return pd.DataFrame(data)

def export_customers_to_edw(db: Session, export_dir: str) -> str:
    """
    Exports all customer data from the CDP to a CSV file for EDW.

    Args:
        db (Session): The SQLAlchemy database session.
        export_dir (str): The directory where the CSV file will be saved.

    Returns:
        str: The full path to the generated CSV file, or an empty string if no data was exported.
    """
    print("Exporting customer data...")
    df = _fetch_data_to_dataframe(db, models.Customer)
    if df.empty:
        print("No customer data found to export.")
        return ""
    filename = os.path.join(export_dir, f"customers_cdp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df.to_csv(filename, index=False)
    print(f"Successfully exported customer data to {filename}")
    return filename

def export_offers_to_edw(db: Session, export_dir: str) -> str:
    """
    Exports all offer data from the CDP to a CSV file for EDW.
    This includes offers of all statuses (active, expired, etc.).

    Args:
        db (Session): The SQLAlchemy database session.
        export_dir (str): The directory where the CSV file will be saved.

    Returns:
        str: The full path to the generated CSV file, or an empty string if no data was exported.
    """
    print("Exporting offer data...")
    df = _fetch_data_to_dataframe(db, models.Offer)
    if df.empty:
        print("No offer data found to export.")
        return ""
    filename = os.path.join(export_dir, f"offers_cdp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df.to_csv(filename, index=False)
    print(f"Successfully exported offer data to {filename}")
    return filename

def export_offer_history_to_edw(db: Session, export_dir: str) -> str:
    """
    Exports offer history data (for the past 6 months as per FR23) to a CSV file for EDW.

    Args:
        db (Session): The SQLAlchemy database session.
        export_dir (str): The directory where the CSV file will be saved.

    Returns:
        str: The full path to the generated CSV file, or an empty string if no data was exported.
    """
    print("Exporting offer history data (last 6 months)...")
    # FR23: maintain offer history for the past 6 months
    df = _fetch_data_to_dataframe(db, models.OfferHistory, date_column="change_timestamp", days_back=180)
    if df.empty:
        print("No offer history data found for the last 6 months to export.")
        return ""
    filename = os.path.join(export_dir, f"offer_history_cdp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df.to_csv(filename, index=False)
    print(f"Successfully exported offer history data to {filename}")
    return filename

def export_campaign_events_to_edw(db: Session, export_dir: str) -> str:
    """
    Exports campaign event data (for the past 3 months as per FR37) to a CSV file for EDW.

    Args:
        db (Session): The SQLAlchemy database session.
        export_dir (str): The directory where the CSV file will be saved.

    Returns:
        str: The full path to the generated CSV file, or an empty string if no data was exported.
    """
    print("Exporting campaign event data (last 3 months)...")
    # FR37: maintain all data in LTFS Offer CDP for previous 3 months before deletion.
    # This implies campaign events relevant for EDW should also be within this window.
    df = _fetch_data_to_dataframe(db, models.CampaignEvent, date_column="event_timestamp", days_back=90)
    if df.empty:
        print("No campaign event data found for the last 3 months to export.")
        return ""
    filename = os.path.join(export_dir, f"campaign_events_cdp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df.to_csv(filename, index=False)
    print(f"Successfully exported campaign event data to {filename}")
    return filename

def run_daily_edw_export():
    """
    Main function to orchestrate the daily EDW data export.
    This function is designed to be called by a scheduled job (e.g., Celery Beat, cron job)
    to fulfill FR36 and NFR11 ("pass data from LTFS Offer CDP to EDW on a daily basis by day end").
    """
    print(f"Starting daily EDW export process at {datetime.now()}")
    exported_files = []
    db = None # Initialize db to None to ensure it's defined for finally block

    try:
        db_gen = get_db()
        db = next(db_gen) # Obtain the database session from the generator

        # Export data from each relevant table
        exported_files.append(export_customers_to_edw(db, EDW_EXPORT_DIR))
        exported_files.append(export_offers_to_edw(db, EDW_EXPORT_DIR))
        exported_files.append(export_offer_history_to_edw(db, EDW_EXPORT_DIR))
        exported_files.append(export_campaign_events_to_edw(db, EDW_EXPORT_DIR))

    except Exception as e:
        print(f"An error occurred during EDW export: {e}")
    finally:
        if db: # Ensure db session was successfully obtained before attempting to close
            try:
                db.close() # Close the database session to release resources
            except Exception as e:
                print(f"Error closing database session: {e}")

    # Filter out any empty strings from the list (which indicate no data was exported for a table)
    successful_exports = [f for f in exported_files if f]
    if successful_exports:
        print(f"Daily EDW export completed successfully. Files generated: {successful_exports}")
    else:
        print("Daily EDW export completed. No new files were generated or all exports failed.")

# This block allows the script to be run directly for testing purposes.
# In a production environment, `run_daily_edw_export()` would typically be invoked
# by a dedicated scheduler service (e.g., Celery Beat, cron).
if __name__ == "__main__":
    print("Running EDW export script directly. This is typically for testing.")
    print(f"Export files will be saved in: {os.path.abspath(EDW_EXPORT_DIR)}")
    # To run this script successfully, ensure your environment has access to
    # a PostgreSQL database configured as per `app.database.get_db`.
    # For a full test, you might need to set up a test database and populate it.
    run_daily_edw_export()