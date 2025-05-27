from flask import Blueprint, jsonify, current_app, send_file
import io
import csv
import pandas as pd
from datetime import datetime

# Define Blueprints for customer-related and data-download routes
customer_bp = Blueprint('customer_bp', __name__, url_prefix='/customers')
data_bp = Blueprint('data_bp', __name__, url_prefix='/data')

# Helper function to get DB connection/session from current_app
# In a real Flask application, `current_app.db` would be initialized
# in `app.py` (e.g., a psycopg2 connection pool, SQLAlchemy session, etc.).
# For the purpose of this file, we assume it provides methods like `fetch_one`
# and `fetch_all` that return dictionaries or similar row objects.
def get_db():
    """
    Retrieves the database connection/session from the current Flask application context.
    """
    if not hasattr(current_app, 'db'):
        # This block is for robustness if `current_app.db` isn't set up
        # in a test environment or if the app context is missing.
        # In a fully running Flask app, this should ideally be pre-configured.
        current_app.logger.error("Database connection not found on current_app.")
        raise RuntimeError("Database connection not configured.")
    return current_app.db


@customer_bp.route('/<string:customer_id>', methods=['GET'])
def get_customer_profile(customer_id):
    """
    Retrieves a single customer's profile view with associated offers and journey stages.
    API Endpoint: GET /customers/{customer_id}
    """
    db = get_db()
    try:
        # Fetch customer basic details
        customer = db.fetch_one(
            "SELECT customer_id, mobile_number, pan_number, segment, dnd_flag "
            "FROM customers WHERE customer_id = %s",
            (customer_id,)
        )

        if not customer:
            return jsonify({"message": "Customer not found"}), 404

        # Fetch associated offers
        offers_raw = db.fetch_all(
            "SELECT offer_id, offer_type, offer_status, propensity, start_date, end_date "
            "FROM offers WHERE customer_id = %s",
            (customer_id,)
        )

        # Format offer dates for JSON serialization
        current_offers = []
        for offer in offers_raw:
            formatted_offer = {
                "offer_id": offer["offer_id"],
                "offer_type": offer["offer_type"],
                "offer_status": offer["offer_status"],
                "propensity": offer["propensity"],
                "start_date": (
                    offer["start_date"].strftime('%Y-%m-%d')
                    if isinstance(offer.get('start_date'), datetime)
                    else str(offer.get('start_date'))
                ),
                "end_date": (
                    offer["end_date"].strftime('%Y-%m-%d')
                    if isinstance(offer.get('end_date'), datetime)
                    else str(offer.get('end_date'))
                ),
            }
            current_offers.append(formatted_offer)

        # Fetch associated events/journey stages
        events_raw = db.fetch_all(
            "SELECT event_type, event_timestamp, event_source, event_details "
            "FROM events WHERE customer_id = %s",
            (customer_id,)
        )

        # Format event timestamps and map 'event_source' to 'source'
        journey_stages = []
        for event in events_raw:
            formatted_event = {
                "event_type": event["event_type"],
                "event_timestamp": (
                    event["event_timestamp"].isoformat()
                    if isinstance(event.get('event_timestamp'), datetime)
                    else str(event.get('event_timestamp'))
                ),
                "source": event["event_source"]
            }
            journey_stages.append(formatted_event)

        customer_profile = {
            "customer_id": customer["customer_id"],
            "mobile_number": customer["mobile_number"],
            "pan_number": customer["pan_number"],
            "segment": customer["segment"],
            "dnd_flag": customer["dnd_flag"],
            "current_offers": current_offers,
            "journey_stages": journey_stages
        }

        return jsonify(customer_profile), 200

    except Exception as e:
        current_app.logger.error(
            f"Error fetching customer profile for {customer_id}: {e}"
        )
        return jsonify({"message": "Internal server error"}), 500


@data_bp.route('/duplicates', methods=['GET'])
def download_duplicate_data():
    """
    Allows download of a file containing identified duplicate customer records.
    API Endpoint: GET /data/duplicates
    """
    db = get_db()
    try:
        # This query assumes a 'duplicate_records' table or view exists
        # that stores the output of the deduplication process.
        duplicate_records = db.fetch_all(
            "SELECT mobile_number, pan_number, aadhaar_number, duplicate_reason, "
            "original_customer_id, duplicate_customer_id "
            "FROM duplicate_records ORDER BY mobile_number"
        )

        if not duplicate_records:
            return jsonify({"message": "No duplicate records found"}), 404

        # Generate CSV in-memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header row based on keys of the first record
        headers = list(duplicate_records[0].keys())
        writer.writerow(headers)

        # Write data rows
        for record in duplicate_records:
            writer.writerow([record[key] for key in headers])

        output.seek(0)  # Rewind to the beginning of the stream
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='duplicate_customer_data.csv'
        )

    except Exception as e:
        current_app.logger.error(f"Error generating duplicate data file: {e}")
        return jsonify({"message": "Internal server error"}), 500


@data_bp.route('/unique', methods=['GET'])
def download_unique_data():
    """
    Allows download of a file containing unique customer records after deduplication.
    API Endpoint: GET /data/unique
    """
    db = get_db()
    try:
        # This query targets the main 'customers' table, which should contain
        # unique customer profiles after the deduplication process.
        unique_records = db.fetch_all(
            "SELECT customer_id, mobile_number, pan_number, aadhaar_number, segment, dnd_flag "
            "FROM customers ORDER BY customer_id"
        )

        if not unique_records:
            return jsonify({"message": "No unique customer records found"}), 404

        # Generate CSV in-memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header row
        headers = list(unique_records[0].keys())
        writer.writerow(headers)

        # Write data rows
        for record in unique_records:
            writer.writerow([record[key] for key in headers])

        output.seek(0)  # Rewind to the beginning of the stream
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='unique_customer_data.csv'
        )

    except Exception as e:
        current_app.logger.error(f"Error generating unique data file: {e}")
        return jsonify({"message": "Internal server error"}), 500


@data_bp.route('/errors', methods=['GET'])
def download_error_file():
    """
    Allows download of an Excel file detailing errors from data ingestion processes.
    API Endpoint: GET /data/errors
    """
    db = get_db()
    try:
        # Query the ingestion_logs table for failed entries
        error_logs = db.fetch_all(
            "SELECT log_id, file_name, upload_timestamp, error_description "
            "FROM ingestion_logs WHERE status = 'FAILED' ORDER BY upload_timestamp DESC"
        )

        if not error_logs:
            return jsonify({"message": "No error logs found"}), 404

        # Convert list of dictionaries to pandas DataFrame for easy Excel export
        df = pd.DataFrame(error_logs)

        # Use BytesIO to save the Excel file in-memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ingestion Errors')
        output.seek(0)  # Rewind to the beginning of the stream

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='ingestion_errors.xlsx'
        )

    except Exception as e:
        current_app.logger.error(f"Error generating error file: {e}")
        return jsonify({"message": "Internal server error"}), 500