import csv
import io
import base64
import uuid
import pandas as pd
from datetime import datetime
import json
import psycopg2
from psycopg2 import extras

# Placeholder for database connection details.
# In a real Flask application, this would typically be loaded from
# configuration (e.g., Flask's app.config) or managed by a database extension.
DB_CONFIG = {
    "host": "localhost",
    "database": "cdp_db",
    "user": "cdp_user",
    "password": "cdp_password"
}

def get_db_connection():
    """Establishes and returns a new database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise

class FileProcessingService:
    """
    Service class for handling file uploads, processing, and generating downloadable reports.
    This service orchestrates data ingestion, validation, and prepares data for export.
    """

    def __init__(self):
        # Dependencies like a dedicated deduplication service or a logger
        # would typically be injected here.
        pass

    def _validate_customer_row(self, row):
        """
        Performs basic column-level validation for a customer data row.
        (FR1: basic column-level validation, NFR3: data quality)
        """
        errors = []
        # Define key identifiers for deduplication and basic presence checks
        required_identifiers = [
            "mobile_number",
            "pan_number",
            "aadhaar_number",
            "ucid_number",
            "loan_application_number",
        ]

        # At least one primary identifier must be present for a valid customer record
        if not any(row.get(col) for col in required_identifiers):
            errors.append(
                "At least one of mobile_number, pan_number, aadhaar_number, "
                "ucid_number, or loan_application_number must be present."
            )

        # Example: Basic type/format checks
        if row.get("mobile_number") and not isinstance(row["mobile_number"], str):
            errors.append("Mobile number must be a string.")
        if row.get("pan_number") and not isinstance(row["pan_number"], str):
            errors.append("PAN number must be a string.")
        # Add more specific validations as per business rules (e.g., regex for PAN/Aadhaar)

        return errors

    def upload_customer_data(self, file_content_base64, file_name, loan_type):
        """
        Handles the upload of customer details file, performs validation,
        deduplication checks, and inserts unique records into the database.
        (FR35: Admin Portal upload, FR36: generate leads, FR37: success file, FR38: error file)
        """
        log_id = str(uuid.uuid4())
        upload_timestamp = datetime.now()
        status = "FAILED"
        file_error_description = None

        success_count = 0
        error_count = 0
        duplicate_count = 0
        row_errors = []  # Stores details of rows that failed validation
        identified_duplicates = []  # Stores details of rows identified as duplicates

        conn = None
        try:
            decoded_content = base64.b64decode(file_content_base64).decode("utf-8")
            df = pd.read_csv(io.StringIO(decoded_content))

            # Convert column names to lowercase for consistent access
            df.columns = df.columns.str.lower()

            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=extras.DictCursor)

            unique_records_to_insert = []

            # Iterate through rows for validation and deduplication checks
            for index, row in df.iterrows():
                row_data = row.to_dict()
                validation_errors = self._validate_customer_row(row_data)

                if validation_errors:
                    error_count += 1
                    row_errors.append(
                        {
                            "row_number": index + 2,  # +1 for 0-index, +1 for header
                            "data": row_data,
                            "errors": validation_errors,
                        }
                    )
                    # Store row-level error in the assumed `ingestion_row_errors` table
                    cur.execute(
                        """
                        INSERT INTO ingestion_row_errors (id, upload_log_id, row_data, error_description, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            log_id,
                            json.dumps(row_data),
                            "; ".join(validation_errors),
                            datetime.now(),
                        ),
                    )
                    continue

                # Deduplication logic (FR3, FR4, FR5, FR6)
                # Check against existing customers in DB using unique identifiers
                identifiers = {
                    "mobile_number": row_data.get("mobile_number"),
                    "pan_number": row_data.get("pan_number"),
                    "aadhaar_number": row_data.get("aadhaar_number"),
                    "ucid_number": row_data.get("ucid_number"),
                    "loan_application_number": row_data.get("loan_application_number"),
                }

                where_clauses = []
                params = []
                for col, val in identifiers.items():
                    if val:
                        where_clauses.append(f"{col} = %s")
                        params.append(val)

                is_duplicate_of_existing = False
                existing_customer_id = None

                if where_clauses:
                    query = f"SELECT customer_id FROM customers WHERE {' OR '.join(where_clauses)}"
                    cur.execute(query, params)
                    existing_record = cur.fetchone()
                    if existing_record:
                        is_duplicate_of_existing = True
                        existing_customer_id = existing_record["customer_id"]
                        duplicate_count += 1
                        identified_duplicates.append(
                            {
                                "row_number": index + 2,
                                "data": row_data,
                                "reason": "Duplicate of existing customer",
                                "original_customer_id": existing_customer_id,
                            }
                        )
                        # Store duplicate in the assumed `customer_duplicates` table
                        cur.execute(
                            """
                            INSERT INTO customer_duplicates (id, upload_log_id, customer_data, duplicate_reason, original_customer_id, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                str(uuid.uuid4()),
                                log_id,
                                json.dumps(row_data),
                                "Duplicate of existing customer",
                                existing_customer_id,
                                datetime.now(),
                            ),
                        )

                if not is_duplicate_of_existing:
                    unique_records_to_insert.append(row_data)

            # Batch insert truly unique records into the customers table
            if unique_records_to_insert:
                insert_values = []
                columns = [
                    "customer_id",
                    "mobile_number",
                    "pan_number",
                    "aadhaar_number",
                    "ucid_number",
                    "loan_application_number",
                    "dnd_flag",
                    "segment",
                    "created_at",
                    "updated_at",
                ]

                for record in unique_records_to_insert:
                    customer_id = str(uuid.uuid4())
                    insert_values.append(
                        (
                            customer_id,
                            record.get("mobile_number"),
                            record.get("pan_number"),
                            record.get("aadhaar_number"),
                            record.get("ucid_number"),
                            record.get("loan_application_number"),
                            record.get("dnd_flag", False),
                            record.get("segment"),
                            datetime.now(),
                            datetime.now(),
                        )
                    )

                try:
                    # Use ON CONFLICT DO NOTHING to handle potential duplicates within the batch
                    # or if a race condition occurs with another insert.
                    # The `duplicate_count` above already captures duplicates against existing DB.
                    insert_query = f"""
                        INSERT INTO customers ({', '.join(columns)})
                        VALUES %s
                        ON CONFLICT (mobile_number) DO NOTHING
                        ON CONFLICT (pan_number) DO NOTHING
                        ON CONFLICT (aadhaar_number) DO NOTHING
                        ON CONFLICT (ucid_number) DO NOTHING
                        ON CONFLICT (loan_application_number) DO NOTHING;
                    """
                    extras.execute_values(
                        cur,
                        insert_query,
                        insert_values,
                        page_size=1000
                    )
                    success_count = cur.rowcount  # Number of rows actually inserted
                    conn.commit()

                except psycopg2.IntegrityError as e:
                    conn.rollback()
                    file_error_description = (
                        f"Database integrity error during batch insert: {e}"
                    )
                    print(file_error_description)
                    status = "FAILED"
                except Exception as e:
                    conn.rollback()
                    file_error_description = f"Error during batch insert: {e}"
                    print(file_error_description)
                    status = "FAILED"

            # Determine final status
            if not row_errors and not file_error_description:
                status = "SUCCESS"
            elif row_errors and not file_error_description:
                status = "PARTIAL_SUCCESS"
                file_error_description = (
                    f"File processed with {len(row_errors)} row-level errors "
                    f"and {len(identified_duplicates)} duplicates."
                )
            else:
                status = "FAILED"

        except pd.errors.EmptyDataError:
            file_error_description = "Uploaded file is empty."
        except pd.errors.ParserError as e:
            file_error_description = f"Could not parse CSV file: {e}"
        except base64.binascii.Error:
            file_error_description = "Invalid base64 encoding."
        except UnicodeDecodeError:
            file_error_description = "Could not decode file content as UTF-8."
        except Exception as e:
            file_error_description = (
                f"An unexpected error occurred during file processing: {e}"
            )
        finally:
            if conn:
                # Log the overall ingestion status in ingestion_logs
                try:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO ingestion_logs (log_id, file_name, upload_timestamp, status, error_description)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (log_id, file_name, upload_timestamp, status, file_error_description),
                    )
                    conn.commit()
                except Exception as e:
                    print(f"Failed to log ingestion status: {e}")
                finally:
                    cur.close()
                    conn.close()

        return {
            "log_id": log_id,
            "status": status,
            "success_count": success_count,
            "error_count": error_count,
            "duplicate_count": duplicate_count,
            "file_error_description": file_error_description,
        }

    def generate_moengage_file(self):
        """
        Generates the Moengage format CSV file for campaigns.
        (FR31: download Moengage file, FR44: Moengage format .csv)
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=extras.DictCursor)

            # FR23: Avoid sending campaigns to DND customers.
            # Select active customers with active offers, excluding DND.
            query = """
                SELECT
                    c.customer_id,
                    c.mobile_number,
                    c.pan_number,
                    c.segment,
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
                    c.customer_id, o.start_date DESC;
            """
            cur.execute(query)
            records = cur.fetchall()

            if not records:
                return None, "No active, non-DND customer data found for Moengage export."

            # Define Moengage specific headers. These would be based on actual Moengage requirements.
            headers = [
                "customer_id",
                "mobile_number",
                "pan_number",
                "segment",
                "offer_id",
                "offer_type",
                "offer_status",
                "propensity",
                "offer_start_date",
                "offer_end_date",
            ]

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)

            for record in records:
                row = [
                    record["customer_id"],
                    record["mobile_number"],
                    record["pan_number"],
                    record["segment"],
                    record["offer_id"],
                    record["offer_type"],
                    record["offer_status"],
                    record["propensity"],
                    record["start_date"].strftime("%Y-%m-%d") if record["start_date"] else "",
                    record["end_date"].strftime("%Y-%m-%d") if record["end_date"] else "",
                ]
                writer.writerow(row)

            return output.getvalue(), None

        except Exception as e:
            return None, f"Error generating Moengage file: {e}"
        finally:
            if conn:
                conn.close()

    def generate_duplicate_file(self):
        """
        Generates a CSV file containing identified duplicate customer records.
        (FR32: download Duplicate Data File)

        This function assumes a `customer_duplicates` table exists in the database
        to store records identified as duplicates during ingestion.
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=extras.DictCursor)

            query = """
                SELECT
                    cd.customer_data,
                    cd.duplicate_reason,
                    cd.original_customer_id,
                    il.file_name,
                    il.upload_timestamp
                FROM
                    customer_duplicates cd
                JOIN
                    ingestion_logs il ON cd.upload_log_id = il.log_id
                ORDER BY
                    il.upload_timestamp DESC, cd.created_at DESC;
            """
            cur.execute(query)
            records = cur.fetchall()

            if not records:
                return None, "No duplicate data found."

            # Dynamically determine headers from the JSONB customer_data
            sample_data = records[0]["customer_data"] if records[0]["customer_data"] else {}
            data_headers = list(sample_data.keys())

            headers = [
                "duplicate_reason",
                "original_customer_id",
                "source_file_name",
                "upload_timestamp",
            ] + data_headers

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)

            for record in records:
                customer_data = record["customer_data"] if record["customer_data"] else {}
                row = [
                    record["duplicate_reason"],
                    record["original_customer_id"],
                    record["file_name"],
                    record["upload_timestamp"].isoformat(),
                ]
                row.extend([customer_data.get(h) for h in data_headers])
                writer.writerow(row)

            return output.getvalue(), None

        except psycopg2.errors.UndefinedTable:
            return None, (
                "Error: 'customer_duplicates' table not found. "
                "This feature requires a table to store identified duplicates."
            )
        except Exception as e:
            return None, f"Error generating duplicate file: {e}"
        finally:
            if conn:
                conn.close()

    def generate_unique_file(self):
        """
        Generates a CSV file containing unique customer records after deduplication.
        (FR33: download Unique Data File)
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=extras.DictCursor)

            query = """
                SELECT
                    customer_id,
                    mobile_number,
                    pan_number,
                    aadhaar_number,
                    ucid_number,
                    loan_application_number,
                    dnd_flag,
                    segment,
                    created_at,
                    updated_at
                FROM
                    customers
                ORDER BY
                    created_at DESC;
            """
            cur.execute(query)
            records = cur.fetchall()

            if not records:
                return None, "No unique customer data found."

            headers = [
                "customer_id",
                "mobile_number",
                "pan_number",
                "aadhaar_number",
                "ucid_number",
                "loan_application_number",
                "dnd_flag",
                "segment",
                "created_at",
                "updated_at",
            ]

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)

            for record in records:
                row = [
                    record["customer_id"],
                    record["mobile_number"],
                    record["pan_number"],
                    record["aadhaar_number"],
                    record["ucid_number"],
                    record["loan_application_number"],
                    record["dnd_flag"],
                    record["segment"],
                    record["created_at"].isoformat(),
                    record["updated_at"].isoformat(),
                ]
                writer.writerow(row)

            return output.getvalue(), None

        except Exception as e:
            return None, f"Error generating unique file: {e}"
        finally:
            if conn:
                conn.close()

    def generate_error_file(self, log_id=None):
        """
        Generates an Excel file detailing errors from data ingestion processes.
        (FR34: download Error Excel file)

        This function assumes an `ingestion_row_errors` table exists in the database
        to store detailed row-level errors from ingestion.
        """
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=extras.DictCursor)

            query = """
                SELECT
                    ire.row_data,
                    ire.error_description,
                    il.file_name,
                    il.upload_timestamp,
                    il.log_id
                FROM
                    ingestion_row_errors ire
                JOIN
                    ingestion_logs il ON ire.upload_log_id = il.log_id
            """
            params = []
            if log_id:
                query += " WHERE il.log_id = %s"
                params.append(log_id)
            query += " ORDER BY il.upload_timestamp DESC, ire.created_at DESC;"

            cur.execute(query, params)
            records = cur.fetchall()

            if not records:
                return None, "No error data found."

            # Dynamically determine headers from the JSONB row_data
            sample_data = records[0]["row_data"] if records[0]["row_data"] else {}
            data_headers = list(sample_data.keys())

            headers = [
                "log_id",
                "source_file_name",
                "upload_timestamp",
                "error_description",
            ] + data_headers

            df_data = []
            for record in records:
                row_data = record["row_data"] if record["row_data"] else {}
                row = {
                    "log_id": record["log_id"],
                    "source_file_name": record["file_name"],
                    "upload_timestamp": record["upload_timestamp"].isoformat(),
                    "error_description": record["error_description"],
                }
                for h in data_headers:
                    row[h] = row_data.get(h)
                df_data.append(row)

            df = pd.DataFrame(df_data, columns=headers)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Errors")
            output.seek(0)

            return output.getvalue(), None

        except psycopg2.errors.UndefinedTable:
            return None, (
                "Error: 'ingestion_row_errors' table not found. "
                "This feature requires a table to store row-level errors."
            )
        except Exception as e:
            return None, f"Error generating error file: {e}"
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    # This block demonstrates how the service might be used and sets up
    # necessary tables for local testing based on the provided DDL and
    # implicitly required tables for FR32 and FR34.

    def setup_test_db():
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            # Create tables from provided DDL if they don't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    mobile_number TEXT UNIQUE,
                    pan_number TEXT UNIQUE,
                    aadhaar_number TEXT UNIQUE,
                    ucid_number TEXT UNIQUE,
                    loan_application_number TEXT UNIQUE,
                    dnd_flag BOOLEAN DEFAULT FALSE,
                    segment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS offers (
                    offer_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    offer_type TEXT,
                    offer_status TEXT,
                    propensity TEXT,
                    start_date DATE,
                    end_date DATE,
                    channel TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ingestion_logs (
                    log_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    error_description TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    event_type TEXT,
                    event_source TEXT,
                    event_timestamp TIMESTAMP,
                    event_details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS campaign_metrics (
                    metric_id TEXT PRIMARY KEY,
                    campaign_unique_id TEXT UNIQUE NOT NULL,
                    campaign_name TEXT,
                    campaign_date DATE,
                    attempted_count INTEGER,
                    sent_success_count INTEGER,
                    failed_count INTEGER,
                    conversion_rate NUMERIC(5,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Create implicitly required tables for FR32 (Duplicate File) and FR34 (Error File)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_duplicates (
                    id TEXT PRIMARY KEY,
                    upload_log_id TEXT REFERENCES ingestion_logs(log_id),
                    customer_data JSONB,
                    duplicate_reason TEXT,
                    original_customer_id TEXT REFERENCES customers(customer_id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ingestion_row_errors (
                    id TEXT PRIMARY KEY,
                    upload_log_id TEXT REFERENCES ingestion_logs(log_id),
                    row_data JSONB,
                    error_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("Test database setup complete (tables created/verified).")
        except Exception as e:
            print(f"Error setting up test database: {e}")
        finally:
            if conn:
                conn.close()

    setup_test_db()

    service = FileProcessingService()

    # --- Test Upload Customer Data ---
    print("\n--- Testing Customer Data Upload ---")
    sample_csv_content = """mobile_number,pan_number,aadhaar_number,segment,dnd_flag
9876543210,ABCDE1234F,123456789012,C1,FALSE
9876543211,ABCDE1234G,123456789013,C2,TRUE
9876543210,,123456789014,C3,FALSE
9876543212,ABCDE1234H,,C4,FALSE
,,,,, # This row will cause validation error
"""
    encoded_csv = base64.b64encode(sample_csv_content.encode("utf-8")).decode("utf-8")
    
    upload_result = service.upload_customer_data(
        encoded_csv, "test_customer_data.csv", "Prospect"
    )
    print(f"Upload Result: {json.dumps(upload_result, indent=2)}")

    # --- Test Generate Moengage File ---
    print("\n--- Testing Moengage File Generation ---")
    moengage_file_content, moengage_error = service.generate_moengage_file()
    if moengage_file_content:
        print("Moengage file content (first 200 chars):\n", moengage_file_content[:200])
    else:
        print(f"Moengage file generation failed: {moengage_error}")

    # --- Test Generate Unique File ---
    print("\n--- Testing Unique File Generation ---")
    unique_file_content, unique_error = service.generate_unique_file()
    if unique_file_content:
        print("Unique file content (first 200 chars):\n", unique_file_content[:200])
    else:
        print(f"Unique file generation failed: {unique_error}")

    # --- Test Generate Duplicate File ---
    print("\n--- Testing Duplicate File Generation ---")
    duplicate_file_content, duplicate_error = service.generate_duplicate_file()
    if duplicate_file_content:
        print("Duplicate file content (first 200 chars):\n", duplicate_file_content[:200])
    else:
        print(f"Duplicate file generation failed: {duplicate_error}")

    # --- Test Generate Error File ---
    print("\n--- Testing Error File Generation ---")
    error_file_content, error_error = service.generate_error_file(
        log_id=upload_result["log_id"]
    )
    if error_file_content:
        with open("test_error_file.xlsx", "wb") as f:
            f.write(error_file_content)
        print("Error file generated: test_error_file.xlsx")
    else:
        print(f"Error file generation failed: {error_error}")

    # Optional: Clean up test data
    def cleanup_test_db():
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("DELETE FROM offers;")
            cur.execute("DELETE FROM customer_duplicates;")
            cur.execute("DELETE FROM ingestion_row_errors;")
            cur.execute("DELETE FROM ingestion_logs;")
            cur.execute("DELETE FROM customers;")
            conn.commit()
            print("Test database cleanup complete.")
        except Exception as e:
            print(f"Error cleaning up test database: {e}")
        finally:
            if conn:
                conn.close()

    # Uncomment the line below to clean up the test database after running
    # cleanup_test_db()