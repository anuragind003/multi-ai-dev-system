import os
import csv
import io
import logging
from datetime import datetime, date

import psycopg2
from psycopg2 import Error
from psycopg2.extras import DictCursor

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Database connection details from environment variables
DB_NAME = os.environ.get("DB_NAME", "cdp_db")
DB_USER = os.environ.get("DB_USER", "cdp_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "cdp_password")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

# Export directory for EDW files
EDW_EXPORT_DIR = os.environ.get("EDW_EXPORT_DIR", "/app/edw_exports")

# Ensure the export directory exists
os.makedirs(EDW_EXPORT_DIR, exist_ok=True)


def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logging.info("Successfully connected to the database.")
        return conn
    except Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None


def export_table_to_csv(conn, table_name, columns, file_path):
    """
    Exports data from a specified table to a CSV file.

    Args:
        conn: The database connection object.
        table_name: The name of the table to export.
        columns: A list of column names to include in the export.
        file_path: The full path to the output CSV file.
    """
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            column_names_str = ", ".join(columns)
            query = f"SELECT {column_names_str} FROM {table_name};"
            cur.execute(query)

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)  # Write header row

                for row in cur:
                    # Convert row values to strings, handling special types
                    processed_row = []
                    for col in columns:
                        value = row[col]
                        if isinstance(value, (datetime, date)):
                            processed_row.append(value.isoformat())
                        elif isinstance(value, dict):  # For JSONB columns
                            processed_row.append(str(value))
                        else:
                            processed_row.append(value)
                    writer.writerow(processed_row)

        logging.info(f"Successfully exported {table_name} to {file_path}")
        return True
    except Error as e:
        logging.error(f"Error exporting {table_name} to CSV: {e}")
        return False
    except IOError as e:
        logging.error(f"Error writing CSV file {file_path}: {e}")
        return False


def daily_edw_export():
    """
    Main function to perform the daily EDW data export.
    Exports data from customers, offers, events, and campaign_metrics tables.
    """
    logging.info("Starting daily EDW data export task.")
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logging.error("Failed to get database connection. Aborting export.")
            return False

        export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Define tables and their columns for export
        tables_to_export = {
            "customers": [
                "customer_id", "mobile_number", "pan_number",
                "aadhaar_number", "ucid_number", "loan_application_number",
                "dnd_flag", "segment", "created_at", "updated_at"
            ],
            "offers": [
                "offer_id", "customer_id", "offer_type", "offer_status",
                "propensity", "start_date", "end_date", "channel",
                "created_at", "updated_at"
            ],
            "events": [
                "event_id", "customer_id", "event_type", "event_source",
                "event_timestamp", "event_details", "created_at"
            ],
            "campaign_metrics": [
                "metric_id", "campaign_unique_id", "campaign_name",
                "campaign_date", "attempted_count", "sent_success_count",
                "failed_count", "conversion_rate", "created_at"
            ]
        }

        all_exports_successful = True
        for table_name, columns in tables_to_export.items():
            file_name = f"edw_export_{table_name}_{export_timestamp}.csv"
            file_path = os.path.join(EDW_EXPORT_DIR, file_name)
            if not export_table_to_csv(conn, table_name, columns, file_path):
                all_exports_successful = False

        if all_exports_successful:
            logging.info("Daily EDW data export completed successfully.")
            return True
        else:
            logging.warning("Daily EDW data export completed with some failures.")
            return False

    except Exception as e:
        logging.critical(f"An unexpected error occurred during EDW export: {e}")
        return False
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")


if __name__ == "__main__":
    # This block allows the script to be run directly for testing
    # In a production Flask app, this would typically be called via a
    # Flask CLI command or a scheduler (e.g., Celery Beat, cron job)
    # that sets up the environment variables.

    # Example of setting environment variables for local testing:
    # os.environ["DB_NAME"] = "your_db_name"
    # os.environ["DB_USER"] = "your_db_user"
    # os.environ["DB_PASSWORD"] = "your_db_password"
    # os.environ["DB_HOST"] = "localhost"
    # os.environ["DB_PORT"] = "5432"
    # os.environ["EDW_EXPORT_DIR"] = "./edw_exports_test"

    if daily_edw_export():
        logging.info("EDW export task finished.")
    else:
        logging.error("EDW export task failed.")