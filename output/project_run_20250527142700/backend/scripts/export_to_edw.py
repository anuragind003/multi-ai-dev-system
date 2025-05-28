import psycopg2
import csv
import os
from datetime import datetime, date, timedelta
import logging

# --- Configuration ---
# Database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'cdp_db')
DB_USER = os.getenv('DB_USER', 'cdp_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'cdp_password')
DB_PORT = os.getenv('DB_PORT', '5432')

# Output directory for exported CSV files
# This directory should be accessible by the script and potentially mounted for EDW ingestion.
EXPORT_DIR = os.getenv('EXPORT_DIR', '/app/exports/edw')

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        logger.info("Successfully connected to the database.")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise

def export_table_to_csv(conn, table_name, date_column, output_dir, export_date=None):
    """
    Exports data from a specified table to a CSV file.
    It exports records where the `date_column` falls within the `export_date`.
    If `export_date` is None, it defaults to today's date.
    """
    if export_date is None:
        export_date = date.today()

    # Define the start and end of the day for the query
    start_of_day = datetime.combine(export_date, datetime.min.time())
    end_of_day = datetime.combine(export_date + timedelta(days=1), datetime.min.time()) # Up to, but not including, next day

    os.makedirs(output_dir, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filepath = os.path.join(output_dir, f"{table_name}_{export_date.strftime('%Y%m%d')}_{timestamp_str}.csv")

    try:
        with conn.cursor() as cur:
            # Get column names for the CSV header
            cur.execute(f"SELECT * FROM {table_name} WHERE FALSE;") # Select no rows, just get metadata
            column_names = [desc[0] for desc in cur.description]

            # Fetch data for the specified date range
            # This query fetches records where the `date_column` is within the `export_date`
            query = f"SELECT * FROM {table_name} WHERE {date_column} >= %s AND {date_column} < %s;"
            cur.execute(query, (start_of_day, end_of_day))
            
            records = cur.fetchall()

            if not records:
                logger.info(f"No new or updated records found for table '{table_name}' for {export_date.strftime('%Y-%m-%d')}. Skipping CSV creation.")
                return

            with open(output_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(column_names) # Write header
                csv_writer.writerows(records) # Write data rows

            logger.info(f"Successfully exported {len(records)} records from '{table_name}' to '{output_filepath}' for date {export_date.strftime('%Y-%m-%d')}.")

    except psycopg2.Error as db_err:
        logger.error(f"Database error during export of '{table_name}': {db_err}")
        raise
    except IOError as io_err:
        logger.error(f"File I/O error during export of '{table_name}': {io_err}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during export of '{table_name}': {e}")
        raise

# --- Main Execution ---
if __name__ == "__main__":
    conn = None
    try:
        conn = get_db_connection()

        # Define tables and their relevant date columns for daily incremental export.
        # The choice of 'updated_at' or 'created_at' depends on whether EDW needs
        # all changes or just newly created records. 'updated_at' is generally
        # more comprehensive for daily snapshots of changes.
        tables_to_export = {
            "customers": "updated_at",
            "offers": "updated_at",
            "offer_history": "status_change_date",
            "events": "event_timestamp",
            "campaigns": "campaign_date"
        }

        # The script is intended to run "daily by day end" (FR28, NFR5).
        # This implies it should export data that was processed or updated *today*.
        export_for_date = date.today()
        logger.info(f"Starting daily EDW export for data dated: {export_for_date.strftime('%Y-%m-%d')}")

        for table, date_col in tables_to_export.items():
            export_table_to_csv(conn, table, date_col, EXPORT_DIR, export_for_date)

        logger.info("EDW export script completed successfully.")

    except Exception as e:
        logger.critical(f"EDW export script failed: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")