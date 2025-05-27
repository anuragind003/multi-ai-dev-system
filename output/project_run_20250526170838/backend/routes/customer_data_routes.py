import csv
import io
import json
from datetime import datetime

import psycopg2
from flask import Blueprint, jsonify, request, send_file, current_app

# Assume a utility for database connection is available.
# In a real application, this would typically be a proper connection pool
# or an ORM setup (e.g., SQLAlchemy) managed centrally.
# For this exercise, we'll provide a simple direct connection function.
def get_db_connection():
    """
    Establishes and returns a new database connection using psycopg2.
    Assumes database configuration is available in Flask's current_app.config.
    """
    try:
        conn = psycopg2.connect(
            host=current_app.config['DB_HOST'],
            database=current_app.config['DB_NAME'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD']
        )
        return conn
    except psycopg2.Error as e:
        current_app.logger.error(f"Database connection error: {e}")
        raise


customer_data_bp = Blueprint('customer_data', __name__, url_prefix='/data')


@customer_data_bp.route('/customers/<customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    """
    Retrieves a single customer's profile view with associated offers
    and journey stages.
    Implements: FR2 (single profile view), FR19 (offer history),
                FR22 (event data), FR26 (application stage data),
                FR40 (customer-level view with stages).
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch customer details
        cur.execute("""
            SELECT customer_id, mobile_number, pan_number, aadhaar_number,
                   ucid_number, dnd_flag, segment
            FROM customers
            WHERE customer_id = %s;
        """, (customer_id,))
        customer = cur.fetchone()

        if not customer:
            return jsonify({"message": "Customer not found"}), 404

        customer_profile = {
            "customer_id": customer[0],
            "mobile_number": customer[1],
            "pan_number": customer[2],
            "aadhaar_number": customer[3],
            "ucid_number": customer[4],
            "dnd_flag": customer[5],
            "segment": customer[6]
        }

        # Fetch associated offers (FR19: Offer history for past 6 months)
        cur.execute("""
            SELECT offer_id, offer_type, offer_status, propensity,
                   start_date, end_date, channel
            FROM offers
            WHERE customer_id = %s
              AND end_date >= (CURRENT_DATE - INTERVAL '6 months')
            ORDER BY start_date DESC;
        """, (customer_id,))
        offers = cur.fetchall()
        customer_profile["current_offers"] = [
            {
                "offer_id": o[0],
                "offer_type": o[1],
                "offer_status": o[2],
                "propensity": o[3],
                "start_date": o[4].isoformat() if o[4] else None,
                "end_date": o[5].isoformat() if o[5] else None,
                "channel": o[6]
            } for o in offers
        ]

        # Fetch journey stages/events (FR22, FR26)
        cur.execute("""
            SELECT event_type, event_source, event_timestamp, event_details
            FROM events
            WHERE customer_id = %s
            ORDER BY event_timestamp ASC;
        """, (customer_id,))
        events = cur.fetchall()
        customer_profile["journey_stages"] = [
            {
                "event_type": e[0],
                "event_source": e[1],
                "event_timestamp": e[2].isoformat() if e[2] else None,
                "event_details": e[3]
            } for e in events
        ]

        return jsonify(customer_profile), 200

    except psycopg2.Error as e:
        current_app.logger.error(
            f"Database error fetching customer profile for {customer_id}: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    except Exception as e:
        current_app.logger.error(
            f"An unexpected error occurred fetching customer profile "
            f"for {customer_id}: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@customer_data_bp.route('/duplicates', methods=['GET'])
def download_duplicate_data():
    """
    Allows download of a file containing identified duplicate customer records.
    Implements: FR32.
    This route assumes the existence of a `deduplication_log` table
    that stores records identified as duplicates during ingestion
    (e.g., those rejected or merged).
    Example DDL for `deduplication_log` (not in provided DDL):
    CREATE TABLE deduplication_log (
        log_id TEXT PRIMARY KEY,
        original_data JSONB, -- The raw incoming record that was a duplicate
        duplicate_reason TEXT, -- e.g., 'Mobile number exists', 'PAN exists'
        status TEXT, -- e.g., 'DUPLICATE_REJECTED', 'MERGED'
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT original_data, duplicate_reason, processed_at
            FROM deduplication_log
            WHERE status = 'DUPLICATE_REJECTED'
            ORDER BY processed_at DESC;
        """)
        duplicate_records = cur.fetchall()

        if not duplicate_records:
            return jsonify({"message": "No duplicate data found"}), 404

        # Prepare CSV in-memory
        si = io.StringIO()
        writer = csv.writer(si)

        # Determine CSV Header dynamically from the first record's JSONB data
        header = ["original_data_json", "duplicate_reason", "processed_at"]
        if duplicate_records and duplicate_records[0][0]:
            try:
                first_data = duplicate_records[0][0]
                # Ensure first_data is a dict (psycopg2 usually converts JSONB)
                if isinstance(first_data, dict):
                    # Extract keys from the JSONB data for the header
                    header = list(first_data.keys()) + \
                             ["duplicate_reason", "processed_at"]
            except Exception as e:
                current_app.logger.warning(
                    f"Could not parse first duplicate record JSON for header: "
                    f"{e}. Using default header."
                )

        writer.writerow(header)

        for record in duplicate_records:
            row_data = []
            original_data_json = record[0]
            reason = record[1]
            processed_at = record[2]

            if isinstance(original_data_json, dict):
                # Populate row based on the determined header keys
                for key in header[:-2]:  # Exclude reason and processed_at
                    row_data.append(original_data_json.get(key, ''))
            else:
                # If original_data_json is not a dict, just put the raw JSON
                row_data.append(json.dumps(original_data_json))

            row_data.extend([reason,
                             processed_at.isoformat() if processed_at else ''])
            writer.writerow(row_data)

        output = si.getvalue()
        si.close()

        return send_file(
            io.BytesIO(output.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='duplicate_customer_data.csv'
        )

    except psycopg2.Error as e:
        current_app.logger.error(
            f"Database error downloading duplicate data: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    except Exception as e:
        current_app.logger.error(
            f"An unexpected error occurred during duplicate data download: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@customer_data_bp.route('/unique', methods=['GET'])
def download_unique_data():
    """
    Allows download of a file containing unique customer records
    after deduplication.
    Implements: FR33.
    This route exports all records from the `customers` table,
    which represents the unique profiles after the deduplication process.
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT customer_id, mobile_number, pan_number, aadhaar_number,
                   ucid_number, dnd_flag, segment, created_at, updated_at
            FROM customers
            ORDER BY created_at DESC;
        """)
        unique_records = cur.fetchall()

        if not unique_records:
            return jsonify({"message": "No unique customer data found"}), 404

        # Prepare CSV in-memory
        si = io.StringIO()
        writer = csv.writer(si)

        # CSV Header - Matches the SELECT statement order
        header = [
            "customer_id", "mobile_number", "pan_number", "aadhaar_number",
            "ucid_number", "dnd_flag", "segment", "created_at", "updated_at"
        ]
        writer.writerow(header)

        for record in unique_records:
            # Convert datetime objects to ISO format strings for CSV
            row = [
                str(record[0]),  # customer_id
                record[1],       # mobile_number
                record[2],       # pan_number
                record[3],       # aadhaar_number
                record[4],       # ucid_number
                str(record[5]),  # dnd_flag
                record[6],       # segment
                record[7].isoformat() if record[7] else '',  # created_at
                record[8].isoformat() if record[8] else ''   # updated_at
            ]
            writer.writerow(row)

        output = si.getvalue()
        si.close()

        return send_file(
            io.BytesIO(output.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='unique_customer_data.csv'
        )

    except psycopg2.Error as e:
        current_app.logger.error(
            f"Database error downloading unique data: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    except Exception as e:
        current_app.logger.error(
            f"An unexpected error occurred during unique data download: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@customer_data_bp.route('/errors', methods=['GET'])
def download_error_data():
    """
    Allows download of an Excel file detailing errors from
    data ingestion processes.
    Implements: FR34.
    Note: Flask's `send_file` does not directly support Excel (.xlsx)
    generation without additional libraries (e.g., `openpyxl`).
    For this MVP, a CSV file is generated, which can be easily opened
    and viewed in Excel.
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT log_id, file_name, upload_timestamp, status,
                   error_description
            FROM ingestion_logs
            WHERE status = 'FAILED'
            ORDER BY upload_timestamp DESC;
        """)
        error_records = cur.fetchall()

        if not error_records:
            return jsonify({"message": "No error logs found"}), 404

        # Prepare CSV in-memory
        si = io.StringIO()
        writer = csv.writer(si)

        # CSV Header
        header = [
            "log_id", "file_name", "upload_timestamp", "status",
            "error_description"
        ]
        writer.writerow(header)

        for record in error_records:
            # Convert datetime objects to ISO format strings for CSV
            row = [
                str(record[0]),  # log_id
                record[1],       # file_name
                record[2].isoformat() if record[2] else '',  # upload_timestamp
                record[3],       # status
                record[4]        # error_description
            ]
            writer.writerow(row)

        output = si.getvalue()
        si.close()

        return send_file(
            io.BytesIO(output.encode('utf-8')),
            mimetype='text/csv',  # Using CSV as a practical alternative to Excel
            as_attachment=True,
            download_name='error_data.csv'  # Renamed to .csv
        )

    except psycopg2.Error as e:
        current_app.logger.error(
            f"Database error downloading error data: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    except Exception as e:
        current_app.logger.error(
            f"An unexpected error occurred during error data download: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()