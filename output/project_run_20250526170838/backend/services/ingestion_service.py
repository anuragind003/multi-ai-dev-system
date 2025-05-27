import uuid
import base64
import io
import csv
from datetime import datetime, timedelta
import logging

# Configure logging for the service
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Database Connection Placeholder ---
# In a real Flask application, you would typically use Flask-SQLAlchemy,
# or a custom database utility that manages connection pools (e.g., psycopg2.pool).
# For this standalone service file, we'll use a simplified mock.
# You would replace this with your actual database connection logic.

class MockDBCursor:
    """A mock database cursor for demonstration purposes."""
    def __init__(self):
        self.fetchone_result = None
        self.fetchall_result = []

    def execute(self, query, params=None):
        logging.debug(f"Executing query: {query} with params: {params}")
        # Simulate some common queries for customer/offer existence
        if "SELECT customer_id FROM customers WHERE" in query:
            # Simulate finding an existing customer for specific identifiers
            # For testing purposes, if 'existing_mobile' is in params, return a mock customer_id
            if params and "existing_mobile" in params:
                self.fetchone_result = (str(uuid.uuid4()),)
            elif params and "existing_pan" in params:
                self.fetchone_result = (str(uuid.uuid4()),)
            else:
                self.fetchone_result = None
        elif "SELECT offer_id FROM offers WHERE" in query:
            self.fetchone_result = None  # Assume no existing offer for simplicity
        else:
            self.fetchone_result = None

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result

    def close(self):
        pass


class MockDBConnection:
    """A mock database connection for demonstration purposes."""
    def cursor(self):
        return MockDBCursor()

    def commit(self):
        logging.debug("Mock DB commit.")
        pass

    def close(self):
        logging.debug("Mock DB connection closed.")
        pass


def get_db_connection():
    """
    Simulates getting a database connection.
    In a real Flask app, this would return a psycopg2 connection
    from a connection pool or a SQLAlchemy session.
    """
    logging.info("Getting mock DB connection.")
    return MockDBConnection()

# --- End Database Connection Placeholder ---


class IngestionService:
    """
    Service class responsible for handling all data ingestion processes,
    including real-time API data and batch file uploads.
    """

    def __init__(self):
        pass

    def _get_customer_by_identifiers(self, cursor, mobile_number=None, pan_number=None,
                                     aadhaar_number=None, ucid_number=None,
                                     loan_application_number=None):
        """
        Helper to find an existing customer by any of the unique identifiers.
        FR3: deduplicate customer data based on Mobile number, Pan number,
        Aadhaar reference number, UCID number, or previous loan application number.
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

        # Prioritize identifiers if multiple are present, or use OR for any match
        # For simplicity, using OR. A real system might have a priority order.
        query = f"SELECT customer_id FROM customers WHERE {' OR '.join(conditions)}"
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else None

    def _insert_or_update_customer(self, conn, cursor, customer_data):
        """
        Inserts a new customer or updates an existing one based on identifiers.
        Returns the customer_id.
        """
        mobile_number = customer_data.get('mobile_number')
        pan_number = customer_data.get('pan_number')
        aadhaar_number = customer_data.get('aadhaar_number')
        ucid_number = customer_data.get('ucid_number')
        loan_application_number = customer_data.get('loan_application_number')
        segment = customer_data.get('segment')
        dnd_flag = customer_data.get('dnd_flag', False)

        customer_id = self._get_customer_by_identifiers(
            cursor, mobile_number, pan_number, aadhaar_number,
            ucid_number, loan_application_number
        )

        if customer_id:
            # Update existing customer
            update_fields = []
            update_params = []

            # Only update if new data is provided and different
            if mobile_number:
                update_fields.append("mobile_number = %s")
                update_params.append(mobile_number)
            if pan_number:
                update_fields.append("pan_number = %s")
                update_params.append(pan_number)
            if aadhaar_number:
                update_fields.append("aadhaar_number = %s")
                update_params.append(aadhaar_number)
            if ucid_number:
                update_fields.append("ucid_number = %s")
                update_params.append(ucid_number)
            if loan_application_number:
                update_fields.append("loan_application_number = %s")
                update_params.append(loan_application_number)
            if segment:
                update_fields.append("segment = %s")
                update_params.append(segment)

            update_fields.append("dnd_flag = %s")
            update_params.append(dnd_flag)
            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                query = f"UPDATE customers SET {', '.join(update_fields)} WHERE customer_id = %s"
                cursor.execute(query, (*update_params, customer_id))
                conn.commit()
            logging.info(f"Updated existing customer: {customer_id}")
        else:
            # Insert new customer
            customer_id = str(uuid.uuid4())
            query = """
                INSERT INTO customers (
                    customer_id, mobile_number, pan_number, aadhaar_number, ucid_number,
                    loan_application_number, dnd_flag, segment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                customer_id, mobile_number, pan_number, aadhaar_number, ucid_number,
                loan_application_number, dnd_flag, segment
            ))
            conn.commit()
            logging.info(f"Inserted new customer: {customer_id}")
        return customer_id

    def process_realtime_lead(self, data):
        """
        FR7, FR11: Receives real-time lead generation data from Insta/E-aggregators.
        Inserts/updates customer data.
        """
        required_fields = ['mobile_number', 'source_channel']
        if not all(field in data for field in required_fields):
            return {"status": "error", "message": "Missing required lead data fields."}, 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            customer_id = self._insert_or_update_customer(conn, cursor, data)

            return {"status": "success", "customer_id": customer_id}, 200
        except Exception as e:
            logging.error(f"Error processing real-time lead: {e}")
            return {"status": "error", "message": f"Internal server error: {e}"}, 500
        finally:
            if conn:
                conn.close()

    def process_realtime_eligibility(self, data):
        """
        FR11: Receives real-time eligibility data from Insta/E-aggregators.
        Updates customer/offer data.
        """
        required_fields = ['customer_id', 'offer_id', 'eligibility_status']
        if not all(field in data for field in required_fields):
            return {"status": "error", "message": "Missing required eligibility data fields."}, 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            customer_id = data['customer_id']
            offer_id = data['offer_id']
            eligibility_status = data['eligibility_status']
            # loan_amount is mentioned in system design but not in DB schema for offers.
            # It could be stored in event_details or a new field. Skipping for now.

            # Check if offer exists and belongs to customer
            cursor.execute("SELECT customer_id FROM offers WHERE offer_id = %s", (offer_id,))
            existing_offer_cust_id = cursor.fetchone()

            if not existing_offer_cust_id or existing_offer_cust_id[0] != customer_id:
                # If offer doesn't exist or doesn't match customer,
                # this might indicate a new offer or an error.
                # For simplicity, we'll create a new offer if not found.
                logging.warning(f"Offer {offer_id} not found or customer mismatch for "
                                f"eligibility update. Creating new offer for customer {customer_id}.")
                offer_id = str(uuid.uuid4())  # Generate new offer_id
                offer_type = data.get('offer_type', 'Fresh')  # Default or infer
                propensity = data.get('propensity', 'Medium')  # Default or infer
                start_date = data.get('start_date', datetime.now().strftime('%Y-%m-%d'))
                end_date = data.get('end_date',
                                    (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
                channel = data.get('source_channel', 'E-aggregator')

                cursor.execute("""
                    INSERT INTO offers (offer_id, customer_id, offer_type, offer_status,
                                        propensity, start_date, end_date, channel)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (offer_id, customer_id, offer_type, eligibility_status,
                      propensity, start_date, end_date, channel))
            else:
                # Update existing offer
                update_fields = ["offer_status = %s", "updated_at = CURRENT_TIMESTAMP"]
                update_params = [eligibility_status]

                query = f"UPDATE offers SET {', '.join(update_fields)} WHERE offer_id = %s"
                cursor.execute(query, (*update_params, offer_id))

            conn.commit()
            return {"status": "success", "message": "Eligibility updated"}, 200
        except Exception as e:
            logging.error(f"Error processing real-time eligibility: {e}")
            return {"status": "error", "message": f"Internal server error: {e}"}, 500
        finally:
            if conn:
                conn.close()

    def process_realtime_status_update(self, data):
        """
        FR11, FR26: Receives real-time application status updates from
        Insta/E-aggregators or LOS.
        Inserts event data and updates relevant customer/offer status.
        """
        required_fields = ['loan_application_number', 'customer_id',
                           'current_stage', 'status_timestamp']
        if not all(field in data for field in required_fields):
            return {"status": "error", "message": "Missing required status update data fields."}, 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            event_id = str(uuid.uuid4())
            customer_id = data['customer_id']
            event_type = data['current_stage']  # Using current_stage as event_type
            event_source = data.get('source', 'LOS')  # Default to LOS
            event_timestamp = data['status_timestamp']
            event_details = {
                "loan_application_number": data['loan_application_number'],
                "current_stage": data['current_stage'],
                "additional_info": data.get('additional_info', {})
            }

            # FR26: Capture and store application stage data
            cursor.execute("""
                INSERT INTO events (event_id, customer_id, event_type, event_source,
                                    event_timestamp, event_details)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (event_id, customer_id, event_type, event_source,
                  event_timestamp, event_details))

            # FR14: Prevent modification of customer offers with a started loan
            # application journey until the application is expired or rejected.
            # This logic would typically involve updating the status of an offer
            # linked to the loan_application_number.
            # For simplicity, this service only logs the event.
            # A dedicated offer management service would handle offer status changes.

            conn.commit()
            return {"status": "success", "message": "Status updated"}, 200
        except Exception as e:
            logging.error(f"Error processing real-time status update: {e}")
            return {"status": "error", "message": f"Internal server error: {e}"}, 500
        finally:
            if conn:
                conn.close()

    def _validate_csv_row(self, row, row_num):
        """
        FR1, NFR3: Perform basic column-level validation.
        This is a placeholder for actual validation rules from
        'Dataset_Validations_UnifiedCL_v1.1 (1).xlsx'.
        """
        errors = []
        # Example validation: mobile_number must be present and numeric
        mobile_number = row.get('mobile_number')
        if not mobile_number:
            errors.append("Mobile number is missing.")
        elif not mobile_number.isdigit():
            errors.append("Mobile number must be numeric.")
        elif len(mobile_number) != 10:  # Assuming 10 digit mobile numbers
            errors.append("Mobile number must be 10 digits.")

        # Example validation: pan_number if present, must be 10 chars alphanumeric
        pan_number = row.get('pan_number')
        if pan_number and (len(pan_number) != 10 or not pan_number.isalnum()):
            errors.append("PAN number must be 10 alphanumeric characters.")

        # Offer type must be present
        offer_type = row.get('offer_type')
        if not offer_type:
            errors.append("Offer type is missing.")

        # Offer dates must be valid if present
        offer_start_date_str = row.get('offer_start_date')
        offer_end_date_str = row.get('offer_end_date')

        for date_str, date_name in [(offer_start_date_str, "Offer start date"),
                                     (offer_end_date_str, "Offer end date")]:
            if date_str:
                try:
                    datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    errors.append(f"{date_name} '{date_str}' is not in YYYY-MM-DD format.")

        return errors

    def process_customer_data_upload(self, file_content_base64, file_name, loan_type):
        """
        FR35, FR36, FR37, FR38: Uploads customer details file via Admin Portal.
        Parses, validates, deduplicates, and inserts/updates data.
        """
        log_id = str(uuid.uuid4())
        success_count = 0
        error_count = 0
        error_details = []  # To store errors for the error file

        conn = None
        try:
            decoded_content = base64.b64decode(file_content_base64).decode('utf-8')
            csv_file = io.StringIO(decoded_content)
            reader = csv.DictReader(csv_file)

            # Check for minimal required headers
            if not all(header in reader.fieldnames for header in ['mobile_number', 'offer_type']):
                raise ValueError("CSV file must contain at least 'mobile_number' and 'offer_type' columns.")

            conn = get_db_connection()
            cursor = conn.cursor()

            for i, row in enumerate(reader):
                row_num = i + 2  # +1 for 0-indexed, +1 for header row
                row_errors = self._validate_csv_row(row, row_num)

                if row_errors:
                    error_count += 1
                    error_details.append({
                        "row_number": row_num,
                        "data": row,
                        "error_desc": "; ".join(row_errors)
                    })
                    continue

                try:
                    # Prepare customer data
                    customer_data = {
                        'mobile_number': row.get('mobile_number'),
                        'pan_number': row.get('pan_number'),
                        'aadhaar_number': row.get('aadhaar_number'),
                        'ucid_number': row.get('ucid_number'),
                        'loan_application_number': row.get('loan_application_number'),
                        'segment': row.get('segment'),
                        'dnd_flag': row.get('dnd_flag', 'FALSE').upper() == 'TRUE'
                    }

                    customer_id = self._insert_or_update_customer(conn, cursor, customer_data)

                    # Prepare offer data
                    offer_type = row.get('offer_type')
                    propensity = row.get('propensity')
                    offer_start_date_str = row.get('offer_start_date')
                    offer_end_date_str = row.get('offer_end_date')

                    offer_start_date = (datetime.strptime(offer_start_date_str, '%Y-%m-%d').date()
                                        if offer_start_date_str else datetime.now().date())
                    offer_end_date = (datetime.strptime(offer_end_date_str, '%Y-%m-%d').date()
                                      if offer_end_date_str else (datetime.now().date() + timedelta(days=30)))

                    # FR16: Maintain flags for Offer statuses (Active, Inactive, Expired)
                    offer_status = 'Active'
                    if offer_end_date < datetime.now().date():
                        offer_status = 'Expired'

                    # FR8: Update old offers in Analytics Offermart with new data received from CDP
                    # For simplicity, we'll insert a new offer. A more robust implementation
                    # would manage offer versions or update existing offers based on business rules.
                    offer_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO offers (offer_id, customer_id, offer_type, offer_status,
                                            propensity, start_date, end_date, channel)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (offer_id, customer_id, offer_type, offer_status,
                          propensity, offer_start_date, offer_end_date, loan_type))  # Using loan_type as channel

                    conn.commit()
                    success_count += 1
                except Exception as row_e:
                    error_count += 1
                    error_details.append({
                        "row_number": row_num,
                        "data": row,
                        "error_desc": f"Processing error: {row_e}"
                    })
                    logging.error(f"Error processing row {row_num}: {row_e}")
                    # In a real scenario, you might want to rollback the current row's
                    # transaction if using a transaction per row, or ensure atomicity.
                    # For this example, we log and continue.

            # Log the overall ingestion result
            status = "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS" if success_count > 0 else "FAILED"
            error_description = "No errors" if error_count == 0 else f"{error_count} errors encountered."

            cursor.execute("""
                INSERT INTO ingestion_logs (log_id, file_name, upload_timestamp, status, error_description)
                VALUES (%s, %s, %s, %s, %s)
            """, (log_id, file_name, datetime.now(), status, error_description))
            conn.commit()

            return {
                "status": status,
                "log_id": log_id,
                "success_count": success_count,
                "error_count": error_count,
                "error_details": error_details  # This can be used by the API layer to generate the error file
            }, 200

        except ValueError as ve:
            logging.error(f"File parsing error: {ve}")
            # Log the ingestion failure in case of file parsing errors
            if conn is None:  # Try to get a connection if it failed before
                conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ingestion_logs (log_id, file_name, upload_timestamp, status, error_description)
                    VALUES (%s, %s, %s, %s, %s)
                """, (log_id, file_name, datetime.now(), "FAILED", f"File parsing error: {ve}"))
                conn.commit()
            return {"status": "error", "message": f"File processing failed: {ve}"}, 400
        except Exception as e:
            logging.error(f"Unexpected error during file upload processing: {e}")
            # Log the ingestion failure for any other unexpected errors
            if conn is None:
                conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ingestion_logs (log_id, file_name, upload_timestamp, status, error_description)
                    VALUES (%s, %s, %s, %s, %s)
                """, (log_id, file_name, datetime.now(), "FAILED", f"Internal server error: {e}"))
                conn.commit()
            return {"status": "error", "message": f"Internal server error: {e}"}, 500
        finally:
            if conn:
                conn.close()