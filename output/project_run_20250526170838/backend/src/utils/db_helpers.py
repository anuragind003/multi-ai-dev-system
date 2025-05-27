import os
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime, date

# Database connection details from environment variables
DB_NAME = os.getenv('DB_NAME', 'cdp_db')
DB_USER = os.getenv('DB_USER', 'cdp_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'cdp_password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

def get_db_connection():
    """Establishes and returns a new database connection."""
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        raise

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Executes a SQL query.
    :param query: The SQL query string.
    :param params: A tuple or list of parameters for the query.
    :param fetch_one: If True, fetches a single row.
    :param fetch_all: If True, fetches all rows.
    :param commit: If True, commits the transaction.
    :return: Query result (single row, all rows, or None for DML).
    """
    conn = None
    cursor = None
    result = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor) # Use RealDictCursor for dict results
        cursor.execute(query, params)
        if commit:
            conn.commit()
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
    except Error as e:
        if conn:
            conn.rollback() # Rollback on error
        print(f"Error executing query: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return result

# --- Specific Helper Functions for CRUD operations based on schema ---

def insert_customer(mobile_number, pan_number=None, aadhaar_number=None, ucid_number=None, loan_application_number=None, dnd_flag=False, segment=None):
    """Inserts a new customer record."""
    customer_id = str(uuid.uuid4())
    query = """
        INSERT INTO customers (customer_id, mobile_number, pan_number, aadhaar_number, ucid_number, loan_application_number, dnd_flag, segment)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING customer_id;
    """
    params = (customer_id, mobile_number, pan_number, aadhaar_number, ucid_number, loan_application_number, dnd_flag, segment)
    try:
        result = execute_query(query, params, fetch_one=True, commit=True)
        return result['customer_id'] if result else None
    except Error as e:
        # Handle potential unique constraint violations
        if "duplicate key value violates unique constraint" in str(e):
            print(f"Customer with provided unique identifier already exists: {e}")
            raise ValueError("Customer with provided unique identifier already exists.")
        raise

def get_customer_by_id(customer_id):
    """Retrieves a customer record by customer_id."""
    query = "SELECT * FROM customers WHERE customer_id = %s;"
    return execute_query(query, (customer_id,), fetch_one=True)

def get_customer_by_identifiers(mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None, loan_application_number=None):
    """
    Retrieves a customer record by any of the unique identifiers.
    Returns the first match found.
    """
    conditions = []
    params = []
    if mobile_number:
        conditions.append("mobile_number = %s")
        params.append(mobile_number)
    if pan_number:
        conditions.append("pan_number = %s")
        params.append(pan_number)
    if aadhaar_number:
        conditions.append("aadhaar_number = %s")
        params.append(aadhaar_number)
    if ucid_number:
        conditions.append("ucid_number = %s")
        params.append(ucid_number)
    if loan_application_number:
        conditions.append("loan_application_number = %s")
        params.append(loan_application_number)

    if not conditions:
        return None

    query = f"SELECT * FROM customers WHERE {' OR '.join(conditions)};"
    return execute_query(query, tuple(params), fetch_one=True)

def update_customer(customer_id, **kwargs):
    """Updates a customer record."""
    set_clauses = []
    params = []
    for key, value in kwargs.items():
        if key in ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number', 'loan_application_number', 'dnd_flag', 'segment']:
            set_clauses.append(f"{key} = %s")
            params.append(value)
    
    if not set_clauses:
        return False # No valid fields to update

    params.append(customer_id) # Add customer_id for WHERE clause
    query = f"UPDATE customers SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE customer_id = %s;"
    try:
        execute_query(query, tuple(params), commit=True)
        return True
    except Error:
        return False

def insert_offer(customer_id, offer_type, offer_status, propensity, start_date, end_date, channel):
    """Inserts a new offer record."""
    offer_id = str(uuid.uuid4())
    query = """
        INSERT INTO offers (offer_id, customer_id, offer_type, offer_status, propensity, start_date, end_date, channel)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING offer_id;
    """
    params = (offer_id, customer_id, offer_type, offer_status, propensity, start_date, end_date, channel)
    result = execute_query(query, params, fetch_one=True, commit=True)
    return result['offer_id'] if result else None

def get_offers_by_customer_id(customer_id):
    """Retrieves all offers for a given customer_id."""
    query = "SELECT * FROM offers WHERE customer_id = %s ORDER BY created_at DESC;"
    return execute_query(query, (customer_id,), fetch_all=True)

def update_offer_status(offer_id, new_status):
    """Updates the status of an offer."""
    query = "UPDATE offers SET offer_status = %s, updated_at = CURRENT_TIMESTAMP WHERE offer_id = %s;"
    execute_query(query, (new_status, offer_id), commit=True)

def insert_event(customer_id, event_type, event_source, event_timestamp, event_details=None):
    """Inserts a new event record."""
    event_id = str(uuid.uuid4())
    query = """
        INSERT INTO events (event_id, customer_id, event_type, event_source, event_timestamp, event_details)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING event_id;
    """
    params = (event_id, customer_id, event_type, event_source, event_timestamp, event_details)
    result = execute_query(query, params, fetch_one=True, commit=True)
    return result['event_id'] if result else None

def get_events_by_customer_id(customer_id, limit=None):
    """Retrieves events for a given customer_id."""
    query = "SELECT * FROM events WHERE customer_id = %s ORDER BY event_timestamp DESC"
    params = [customer_id]
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    return execute_query(query, tuple(params), fetch_all=True)

def insert_campaign_metric(campaign_unique_id, campaign_name, campaign_date, attempted_count, sent_success_count, failed_count, conversion_rate):
    """Inserts a new campaign metric record."""
    metric_id = str(uuid.uuid4())
    query = """
        INSERT INTO campaign_metrics (metric_id, campaign_unique_id, campaign_name, campaign_date, attempted_count, sent_success_count, failed_count, conversion_rate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING metric_id;
    """
    params = (metric_id, campaign_unique_id, campaign_name, campaign_date, attempted_count, sent_success_count, failed_count, conversion_rate)
    result = execute_query(query, params, fetch_one=True, commit=True)
    return result['metric_id'] if result else None

def log_ingestion_event(file_name, status, error_description=None):
    """Logs an ingestion event."""
    log_id = str(uuid.uuid4())
    query = """
        INSERT INTO ingestion_logs (log_id, file_name, status, error_description)
        VALUES (%s, %s, %s, %s)
        RETURNING log_id;
    """
    params = (log_id, file_name, status, error_description)
    result = execute_query(query, params, fetch_one=True, commit=True)
    return result['log_id'] if result else None

def get_ingestion_logs(status=None, limit=None):
    """Retrieves ingestion logs, optionally filtered by status."""
    query = "SELECT * FROM ingestion_logs"
    params = []
    if status:
        query += " WHERE status = %s"
        params.append(status)
    query += " ORDER BY upload_timestamp DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    return execute_query(query, tuple(params), fetch_all=True)

# --- Deduplication related helpers ---
def get_all_customers_for_deduplication():
    """
    Retrieves essential customer identifiers for deduplication.
    This might be used by a batch deduplication process.
    """
    query = "SELECT customer_id, mobile_number, pan_number, aadhaar_number, ucid_number, loan_application_number FROM customers;"
    return execute_query(query, fetch_all=True)

def get_active_offers_for_customer(customer_id):
    """
    Retrieves active offers for a customer, potentially for attribution logic.
    """
    query = "SELECT * FROM offers WHERE customer_id = %s AND offer_status = 'Active';"
    return execute_query(query, (customer_id,), fetch_all=True)

def get_dnd_customers():
    """Retrieves customer IDs marked as DND."""
    query = "SELECT customer_id FROM customers WHERE dnd_flag = TRUE;"
    return [c['customer_id'] for c in execute_query(query, fetch_all=True)]

def delete_old_data(table_name, retention_months, date_column='created_at'):
    """
    Deletes data older than a specified retention period.
    This would be part of a scheduled cleanup job.
    """
    query = f"DELETE FROM {table_name} WHERE {date_column} < (CURRENT_TIMESTAMP - INTERVAL '%s months');"
    try:
        execute_query(query, (retention_months,), commit=True)
        print(f"Successfully deleted old data from {table_name}.")
        return True
    except Error as e:
        print(f"Error deleting old data from {table_name}: {e}")
        return False