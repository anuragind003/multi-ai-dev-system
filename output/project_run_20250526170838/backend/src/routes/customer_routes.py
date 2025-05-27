import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
import psycopg2
from psycopg2 import errors as pg_errors

# Assuming a database utility module exists at backend.src.utils.db
# This module would handle connection pooling, execution, and closing.
# For this exercise, we'll mock these functions or provide a basic implementation.

# --- Mock Database Utility Functions (Replace with actual implementation) ---
# In a real application, these would be in a separate module (e.g., backend/src/utils/db.py)
# and handle connection pooling, error handling, etc.

_conn = None # Placeholder for a single connection for demonstration

def get_db_connection():
    """Establishes and returns a database connection."""
    global _conn
    if _conn is None or _conn.closed:
        try:
            # Replace with your actual PostgreSQL connection details
            _conn = psycopg2.connect(
                host="localhost",
                database="cdp_db",
                user="cdp_user",
                password="cdp_password"
            )
            _conn.autocommit = False # Manage transactions manually
        except pg_errors.OperationalError as e:
            print(f"Database connection error: {e}")
            raise ConnectionError("Could not connect to the database.") from e
    return _conn

def close_db_connection(conn):
    """Closes the database connection."""
    # In a real app with connection pooling, this might return the connection to the pool.
    # For this simple example, we'll just commit and close if it's the global connection.
    global _conn
    if conn and conn == _conn:
        try:
            conn.commit()
            conn.close()
            _conn = None
        except Exception as e:
            print(f"Error closing database connection: {e}")

def execute_query(query, params=None, fetch_type=None):
    """Executes a SQL query and optionally fetches results."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch_type == 'one':
            return cursor.fetchone()
        elif fetch_type == 'all':
            return cursor.fetchall()
        else:
            conn.commit() # Commit changes for non-SELECT queries
            return None
    except pg_errors.IntegrityError as e:
        if conn:
            conn.rollback()
        raise ValueError(f"Data integrity error: {e}") from e
    except pg_errors.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
        raise RuntimeError(f"Database operation failed: {e}") from e
    finally:
        if cursor:
            cursor.close()
        # In a real app, you might not close the connection here if using pooling.
        # For this simple example, we'll keep it open until explicitly closed or app shutdown.
        # close_db_connection(conn) # Don't close here if using a global connection for multiple calls

def fetch_one(query, params=None):
    return execute_query(query, params, fetch_type='one')

def fetch_all(query, params=None):
    return execute_query(query, params, fetch_type='all')

# --- End Mock Database Utility Functions ---


customer_bp = Blueprint('customer_bp', __name__)

@customer_bp.route('/customers/<customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    """
    Retrieves a single customer's profile view with associated offers and journey stages.
    FR2: The system shall provide a single profile view of the customer for Consumer Loan Products.
    FR40: The system shall provide a front-end for customer-level view with stages.
    """
    if not customer_id:
        return jsonify({"error": "Customer ID is required"}), 400

    try:
        # Fetch customer details
        customer_query = """
            SELECT customer_id, mobile_number, pan_number, aadhaar_number, ucid_number,
                   loan_application_number, dnd_flag, segment
            FROM customers
            WHERE customer_id = %s;
        """
        customer_data = fetch_one(customer_query, (customer_id,))

        if not customer_data:
            return jsonify({"error": "Customer not found"}), 404

        customer_profile = {
            "customer_id": customer_data[0],
            "mobile_number": customer_data[1],
            "pan_number": customer_data[2],
            "aadhaar_number": customer_data[3],
            "ucid_number": customer_data[4],
            "loan_application_number": customer_data[5],
            "dnd_flag": customer_data[6],
            "segment": customer_data[7],
            "current_offers": [],
            "journey_stages": []
        }

        # Fetch associated offers
        offers_query = """
            SELECT offer_id, offer_type, offer_status, propensity, start_date, end_date, channel
            FROM offers
            WHERE customer_id = %s;
        """
        offers_data = fetch_all(offers_query, (customer_id,))
        for offer in offers_data:
            customer_profile["current_offers"].append({
                "offer_id": offer[0],
                "offer_type": offer[1],
                "offer_status": offer[2],
                "propensity": offer[3],
                "start_date": offer[4].isoformat() if offer[4] else None,
                "end_date": offer[5].isoformat() if offer[5] else None,
                "channel": offer[6]
            })

        # Fetch associated events/journey stages
        events_query = """
            SELECT event_type, event_source, event_timestamp, event_details
            FROM events
            WHERE customer_id = %s
            ORDER BY event_timestamp DESC;
        """
        events_data = fetch_all(events_query, (customer_id,))
        for event in events_data:
            customer_profile["journey_stages"].append({
                "event_type": event[0],
                "event_source": event[1],
                "event_timestamp": event[2].isoformat() if event[2] else None,
                "event_details": event[3]
            })

        return jsonify(customer_profile), 200

    except ConnectionError as e:
        return jsonify({"error": str(e)}), 500
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@customer_bp.route('/api/leads', methods=['POST'])
def receive_lead_data():
    """
    Receives real-time lead generation data from Insta/E-aggregators and inserts into CDP.
    FR7: The system shall push real-time offers from Insta or E-aggregators (via APIs) to Analytics Offermart on an hourly/daily basis.
    FR11: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation, Eligibility, Status APIs).
    FR12: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    FR3: The system shall deduplicate customer data based on Mobile number, Pan number, Aadhaar reference number, UCID number, or previous loan application number.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    mobile_number = data.get('mobile_number')
    pan_number = data.get('pan_number')
    aadhaar_number = data.get('aadhaar_number')
    loan_type = data.get('loan_type')
    source_channel = data.get('source_channel')
    ucid_number = data.get('ucid_number') # Optional, but part of deduplication criteria
    loan_application_number = data.get('loan_application_number') # Optional, but part of deduplication criteria

    if not mobile_number and not pan_number and not aadhaar_number:
        return jsonify({"error": "At least one of mobile_number, pan_number, or aadhaar_number is required"}), 400

    try:
        # Deduplication logic: Check if customer already exists based on unique identifiers
        existing_customer_id = None
        dedup_query = """
            SELECT customer_id FROM customers
            WHERE mobile_number = %s OR pan_number = %s OR aadhaar_number = %s
            LIMIT 1;
        """
        # Prioritize exact matches on provided unique identifiers
        if mobile_number or pan_number or aadhaar_number:
            existing_customer = fetch_one(dedup_query, (mobile_number, pan_number, aadhaar_number))
            if existing_customer:
                existing_customer_id = existing_customer[0]

        if existing_customer_id:
            # Customer already exists, return existing ID.
            # In a more complex scenario, this might trigger an update or merge process.
            return jsonify({
                "status": "success",
                "message": "Customer already exists, returning existing ID.",
                "customer_id": existing_customer_id
            }), 200
        else:
            # No existing customer found, create a new one
            new_customer_id = str(uuid.uuid4())
            insert_query = """
                INSERT INTO customers (
                    customer_id, mobile_number, pan_number, aadhaar_number, ucid_number,
                    loan_application_number, segment, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """
            # Segment can be derived later or passed if available. For now, default to 'Prospect' or None.
            segment = "Prospect" # Default segment for new leads
            execute_query(insert_query, (
                new_customer_id, mobile_number, pan_number, aadhaar_number, ucid_number,
                loan_application_number, segment
            ))

            return jsonify({
                "status": "success",
                "message": "New customer created.",
                "customer_id": new_customer_id
            }), 201

    except ValueError as e: # For IntegrityError from execute_query
        return jsonify({"error": str(e)}), 409 # Conflict if unique constraint violated unexpectedly
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 500
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@customer_bp.route('/api/eligibility', methods=['POST'])
def update_eligibility_data():
    """
    Receives real-time eligibility data from Insta/E-aggregators and updates customer/offer data.
    FR7, FR11, FR12
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    customer_id = data.get('customer_id')
    offer_id = data.get('offer_id')
    eligibility_status = data.get('eligibility_status')
    loan_amount = data.get('loan_amount')

    if not all([customer_id, offer_id, eligibility_status]):
        return jsonify({"error": "customer_id, offer_id, and eligibility_status are required"}), 400

    try:
        # Validate customer and offer existence (optional but good practice)
        customer_exists = fetch_one("SELECT 1 FROM customers WHERE customer_id = %s;", (customer_id,))
        if not customer_exists:
            return jsonify({"error": "Customer not found"}), 404

        offer_exists = fetch_one("SELECT 1 FROM offers WHERE offer_id = %s AND customer_id = %s;", (offer_id, customer_id))
        if not offer_exists:
            return jsonify({"error": "Offer not found for this customer"}), 404

        # Update offer details
        update_query = """
            UPDATE offers
            SET offer_status = %s,
                loan_amount = %s, -- Assuming loan_amount can be stored in offers table or related
                updated_at = CURRENT_TIMESTAMP
            WHERE offer_id = %s AND customer_id = %s;
        """
        # Note: The `offers` table schema provided in system design does not explicitly have `loan_amount`.
        # For this implementation, I'll assume it can be added or handled via `event_details` if not.
        # For now, I'll omit `loan_amount` from the update query if it's not in the schema.
        # Let's stick to the provided schema: offer_status is the only direct update.
        update_query = """
            UPDATE offers
            SET offer_status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE offer_id = %s AND customer_id = %s;
        """
        execute_query(update_query, (eligibility_status, offer_id, customer_id))

        # Optionally, log this as an event
        event_id = str(uuid.uuid4())
        event_details = {
            "eligibility_status": eligibility_status,
            "loan_amount": loan_amount # Store loan_amount in event_details
        }
        event_query = """
            INSERT INTO events (event_id, customer_id, event_type, event_source, event_timestamp, event_details)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s);
        """
        execute_query(event_query, (event_id, customer_id, 'ELIGIBILITY_UPDATE', 'E-aggregator/Insta', event_details))

        return jsonify({"status": "success", "message": "Eligibility updated"}), 200

    except ConnectionError as e:
        return jsonify({"error": str(e)}), 500
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@customer_bp.route('/api/status-updates', methods=['POST'])
def receive_status_updates():
    """
    Receives real-time application status updates from Insta/E-aggregators or LOS.
    FR7, FR11, FR12, FR26: The system shall capture and store application stage data.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    loan_application_number = data.get('loan_application_number')
    customer_id = data.get('customer_id')
    current_stage = data.get('current_stage')
    status_timestamp_str = data.get('status_timestamp')
    event_source = data.get('event_source') # e.g., 'LOS', 'E-aggregator', 'Moengage'
    event_type = data.get('event_type') # e.g., 'LOAN_LOGIN', 'BUREAU_CHECK', 'EKYC_ACHIEVED', 'DISBURSEMENT'
    event_details = data.get('event_details', {}) # Additional flexible details

    if not all([customer_id, current_stage, event_source, event_type]):
        return jsonify({"error": "customer_id, current_stage, event_source, and event_type are required"}), 400

    try:
        status_timestamp = datetime.fromisoformat(status_timestamp_str) if status_timestamp_str else datetime.now()

        # Validate customer existence
        customer_exists = fetch_one("SELECT 1 FROM customers WHERE customer_id = %s;", (customer_id,))
        if not customer_exists:
            return jsonify({"error": "Customer not found"}), 404

        # Insert into events table
        event_id = str(uuid.uuid4())
        insert_query = """
            INSERT INTO events (event_id, customer_id, event_type, event_source, event_timestamp, event_details)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        # Add loan_application_number to event_details if present
        if loan_application_number:
            event_details['loan_application_number'] = loan_application_number
        event_details['current_stage'] = current_stage # Ensure current_stage is always in details

        execute_query(insert_query, (
            event_id, customer_id, event_type, event_source, status_timestamp, event_details
        ))

        # FR14: The system shall prevent modification of customer offers with a started loan application journey until the application is expired or rejected.
        # This logic would typically be handled by a separate service that monitors events and updates offer statuses,
        # or by a more complex offer update API that checks journey status.
        # For this endpoint, we are only recording the event.

        return jsonify({"status": "success", "message": "Status updated"}), 200

    except ValueError as e:
        return jsonify({"error": f"Invalid timestamp format: {str(e)}"}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 500
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500