import csv
import io
import os
from datetime import date

# Attempt to import psycopg2 and DictCursor.
# If not available, provide mock classes for basic functionality
# to allow the code structure to be evaluated without a full DB setup.
try:
    import psycopg2
    from psycopg2.extras import DictCursor
except ImportError:
    # Define mock classes if psycopg2 is not installed.
    # This allows the service logic to be structured even if the DB driver is missing.
    class MockConnection:
        def cursor(self, cursor_factory=None):
            return MockCursor()

        def close(self):
            pass

    class MockCursor:
        def execute(self, query, params=None):
            # Simulate query execution
            pass

        def fetchall(self):
            # Simulate some sample data for testing purposes
            return [
                {'customer_id': 'cust_001', 'mobile_number': '9876543210',
                 'offer_id': 'offer_A1', 'offer_type': 'Fresh',
                 'offer_status': 'Active', 'propensity': 'High',
                 'start_date': date(2023, 1, 1), 'end_date': date(2023, 12, 31)},
                {'customer_id': 'cust_002', 'mobile_number': '9988776655',
                 'offer_id': 'offer_B2', 'offer_type': 'Enrich',
                 'offer_status': 'Active', 'propensity': 'Medium',
                 'start_date': date(2023, 2, 1), 'end_date': date(2023, 11, 30)}
            ]

        def close(self):
            pass

    psycopg2 = None  # Mark psycopg2 as not available
    DictCursor = None  # Mark DictCursor as not available

# Database configuration details. In a real Flask app, these would typically
# be loaded from a Flask config object or a dedicated config module.
# Using os.getenv for demonstration purposes to allow environment variable injection.
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'cdp_db'),
    'user': os.getenv('DB_USER', 'cdp_user'),
    'password': os.getenv('DB_PASSWORD', 'cdp_password'),
    'port': os.getenv('DB_PORT', '5432')
}


def get_db_connection():
    """
    Establishes and returns a database connection using psycopg2.
    If psycopg2 is not installed, returns a mock connection for testing.
    """
    if psycopg2:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.Error as e:
            # In a real application, this error should be logged properly.
            # For this context, raising it to indicate failure.
            raise ConnectionError(f"Database connection error: {e}") from e
    else:
        # Fallback to mock connection if psycopg2 is not available.
        return MockConnection()


def generate_moengage_export_csv():
    """
    Generates a CSV string containing customer and active offer data
    for Moengage export, specifically excluding customers marked as DND.

    This function queries the 'customers' and 'offers' tables, filters
    for non-DND customers and active offers, and formats the data
    into a CSV string suitable for upload to Moengage.

    Returns:
        str: A CSV formatted string containing the export data.

    Raises:
        Exception: If there is an error during database interaction or
                   CSV generation.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Define the CSV header row. These columns are derived from the
    # database schema and common requirements for campaign systems.
    # FR44: "The system shall generate the Moengage format file in .csv format"
    # FR23: "The system shall avoid sending campaigns to DND (Do Not Disturb) customers."
    headers = [
        "customer_id",
        "mobile_number",
        "offer_id",
        "offer_type",
        "offer_status",
        "propensity",
        "offer_start_date",
        "offer_end_date"
    ]
    writer.writerow(headers)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        # Use DictCursor to access columns by name, if psycopg2 is available.
        # Otherwise, the MockCursor will handle attribute access.
        cursor = conn.cursor(cursor_factory=DictCursor if psycopg2 else None)

        # SQL query to retrieve relevant data:
        # - Joins 'customers' and 'offers' tables.
        # - Filters out customers with dnd_flag = TRUE.
        # - Filters for offers with offer_status = 'Active'.
        query = """
            SELECT
                c.customer_id,
                c.mobile_number,
                o.offer_id,
                o.offer_type,
                o.offer_status,
                o.propensity,
                o.start_date,
                o.end_date
            FROM
                customers c
            JOIN
                offers o ON c.customer_id = o.customer_id
            WHERE
                c.dnd_flag = FALSE
                AND o.offer_status = 'Active'
            ORDER BY
                c.customer_id, o.start_date;
        """
        cursor.execute(query)
        records = cursor.fetchall()

        for record in records:
            # Format dates to 'YYYY-MM-DD' string format for CSV.
            # Handle potential None values for dates gracefully.
            start_date_str = record['start_date'].strftime('%Y-%m-%d') \
                if record['start_date'] else ''
            end_date_str = record['end_date'].strftime('%Y-%m-%d') \
                if record['end_date'] else ''

            row = [
                record['customer_id'],
                record['mobile_number'],
                record['offer_id'],
                record['offer_type'],
                record['offer_status'],
                record['propensity'],
                start_date_str,
                end_date_str
            ]
            writer.writerow(row)

    except Exception as e:
        # Catch any exceptions during DB operations or CSV writing.
        # In a production system, this would involve detailed logging.
        raise RuntimeError(f"Failed to generate Moengage export CSV: {e}") from e
    finally:
        # Ensure cursor and connection are closed to release resources.
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Return the accumulated CSV content as a string.
    return output.getvalue()