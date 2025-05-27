import io
import csv
import openpyxl
import psycopg2
from psycopg2 import extras
from flask import Blueprint, send_file, jsonify, current_app, request

# Define the Blueprint for reports
bp = Blueprint('reports', __name__, url_prefix='/reports')

def get_db_connection():
    """
    Establishes a new database connection using configuration from the Flask app.
    In a larger application, this function might reside in a separate `database.py`
    module or be managed by a Flask extension like Flask-SQLAlchemy.
    """
    try:
        conn = psycopg2.connect(
            host=current_app.config['DB_HOST'],
            database=current_app.config['DB_NAME'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD']
        )
        return conn
    except Exception as e:
        current_app.logger.error(f"Database connection failed: {e}")
        raise # Re-raise to be caught by the route's error handler

@bp.route('/moengage-export', methods=['GET'])
def moengage_export():
    """
    Generates and allows download of the Moengage format CSV file for campaigns.
    Filters for active offers and non-DND customers.
    (FR31: Download Moengage format file, FR44: Generate Moengage format CSV)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=extras.DictCursor)

        # Query to fetch customer and offer data for Moengage export.
        # Filters: non-DND customers (FR23), active offers (FR16), and offers not yet expired (FR41).
        cur.execute("""
            SELECT
                c.customer_id,
                c.mobile_number,
                c.pan_number,
                c.aadhaar_number,
                c.segment,
                o.offer_id,
                o.offer_type,
                o.offer_status,
                o.propensity,
                o.start_date,
                o.end_date,
                o.channel
            FROM
                customers c
            JOIN
                offers o ON c.customer_id = o.customer_id
            WHERE
                c.dnd_flag = FALSE
                AND o.offer_status = 'Active'
                AND o.end_date >= CURRENT_DATE
            ORDER BY
                c.customer_id, o.offer_id
        """)
        records = cur.fetchall()

        if not records:
            return jsonify({"message": "No active offers found for Moengage export."}), 404

        # Prepare CSV in-memory
        output = io.StringIO()
        writer = csv.writer(output)

        # CSV Header (example, adjust based on actual Moengage format requirements)
        header = [
            "customer_id", "mobile_number", "pan_number", "aadhaar_number",
            "segment", "offer_id", "offer_type", "offer_status",
            "propensity", "offer_start_date", "offer_end_date", "channel"
        ]
        writer.writerow(header)

        for row in records:
            writer.writerow([
                row['customer_id'],
                row['mobile_number'],
                row['pan_number'],
                row['aadhaar_number'],
                row['segment'],
                row['offer_id'],
                row['offer_type'],
                row['offer_status'],
                row['propensity'],
                row['start_date'].isoformat() if row['start_date'] else '',
                row['end_date'].isoformat() if row['end_date'] else '',
                row['channel']
            ])

        output.seek(0) # Rewind to the beginning of the stream

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='moengage_campaign_data.csv'
        )

    except psycopg2.Error as e:
        current_app.logger.error(f"Database error during Moengage export: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during Moengage export: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

@bp.route('/duplicates', methods=['GET'])
def download_duplicates():
    """
    Allows download of a file containing identified duplicate customer records.
    (FR32: Download Duplicate Data File)
    This endpoint assumes that 'duplicate data' refers to records in the
    'ingestion_logs' table that failed specifically due to duplicate detection
    during data ingestion. A more comprehensive solution might involve a
    dedicated 'deduplication_log' table storing details of merged/rejected duplicates.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=extras.DictCursor)

        # Query ingestion_logs for records explicitly marked as duplicates in error_description.
        # This is a pragmatic assumption given the provided schema and distinct FRs for duplicates and errors.
        cur.execute("""
            SELECT
                log_id,
                file_name,
                upload_timestamp,
                error_description
            FROM
                ingestion_logs
            WHERE
                status = 'FAILED' AND error_description ILIKE '%duplicate%'
            ORDER BY
                upload_timestamp DESC
        """)
        records = cur.fetchall()

        if not records:
            return jsonify({"message": "No duplicate records found in ingestion logs."}), 404

        output = io.StringIO()
        writer = csv.writer(output)

        header = ["log_id", "file_name", "upload_timestamp", "error_description"]
        writer.writerow(header)

        for row in records:
            writer.writerow([
                row['log_id'],
                row['file_name'],
                row['upload_timestamp'].isoformat() if row['upload_timestamp'] else '',
                row['error_description']
            ])

        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='duplicate_data_log.csv'
        )

    except psycopg2.Error as e:
        current_app.logger.error(f"Database error during duplicate data export: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during duplicate data export: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

@bp.route('/unique', methods=['GET'])
def download_unique_data():
    """
    Allows download of a file containing unique customer records after deduplication.
    (FR33: Download Unique Data File)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=extras.DictCursor)

        # Fetch all unique customer records from the 'customers' table
        cur.execute("""
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
                created_at DESC
        """)
        records = cur.fetchall()

        if not records:
            return jsonify({"message": "No unique customer records found."}), 404

        output = io.StringIO()
        writer = csv.writer(output)

        header = [
            "customer_id", "mobile_number", "pan_number", "aadhaar_number",
            "ucid_number", "loan_application_number", "dnd_flag", "segment",
            "created_at", "updated_at"
        ]
        writer.writerow(header)

        for row in records:
            writer.writerow([
                row['customer_id'],
                row['mobile_number'],
                row['pan_number'],
                row['aadhaar_number'],
                row['ucid_number'],
                row['loan_application_number'],
                row['dnd_flag'],
                row['segment'],
                row['created_at'].isoformat() if row['created_at'] else '',
                row['updated_at'].isoformat() if row['updated_at'] else ''
            ])

        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='unique_customer_data.csv'
        )

    except psycopg2.Error as e:
        current_app.logger.error(f"Database error during unique data export: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during unique data export: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

@bp.route('/errors', methods=['GET'])
def download_error_file():
    """
    Allows download of an Excel file detailing errors from data ingestion processes.
    (FR34: Download Error Excel file)
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=extras.DictCursor)

        # Fetch all failed ingestion logs
        cur.execute("""
            SELECT
                log_id,
                file_name,
                upload_timestamp,
                status,
                error_description
            FROM
                ingestion_logs
            WHERE
                status = 'FAILED'
            ORDER BY
                upload_timestamp DESC
        """)
        records = cur.fetchall()

        if not records:
            return jsonify({"message": "No error logs found."}), 404

        # Create an in-memory Excel workbook
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Ingestion Errors"

        # Excel Header
        header = ["Log ID", "File Name", "Upload Timestamp", "Status", "Error Description"]
        sheet.append(header)

        for row in records:
            sheet.append([
                row['log_id'],
                row['file_name'],
                row['upload_timestamp'], # openpyxl handles datetime objects directly
                row['status'],
                row['error_description']
            ])

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='ingestion_errors.xlsx'
        )

    except psycopg2.Error as e:
        current_app.logger.error(f"Database error during error file export: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during error file export: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()