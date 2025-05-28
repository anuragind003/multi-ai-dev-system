from flask import Blueprint, make_response, send_file, jsonify, request
import io
import datetime

# Import the service layer that handles the actual data retrieval and file generation.
# This promotes separation of concerns, keeping route logic clean.
# Based on the project structure `backend/src/routes/export_routes.py`
# and the assumption that services are in `backend/src/services/`
from backend.src.services.export_service import ExportService

# Define the Blueprint for export-related routes
exports_bp = Blueprint('exports_bp', __name__, url_prefix='/exports')

@exports_bp.route('/moengage-campaign-file', methods=['GET'])
def download_moengage_campaign_file():
    """
    Generates and allows download of a Moengage-formatted CSV file for eligible customers,
    excluding DND customers.

    Functional Requirements Addressed:
    - FR30: The CDP system shall provide a screen for users to download the Moengage-formatted file (.csv).
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Moengage, Duplicate, Unique, Error).
    - API Endpoint: /exports/moengage-campaign-file (GET)
    """
    try:
        # The service layer is responsible for fetching data, applying business logic
        # (e.g., excluding DND customers), and formatting it into a CSV.
        # It should return a BytesIO object containing the CSV data.
        csv_buffer = ExportService.generate_moengage_file()
        csv_buffer.seek(0) # Rewind the buffer to the beginning

        # Use send_file for proper file download handling
        return send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'moengage_campaign_{datetime.date.today().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error generating Moengage campaign file: {e}")
        return jsonify({"error": "Failed to generate Moengage campaign file", "details": str(e)}), 500

@exports_bp.route('/duplicate-customers', methods=['GET'])
def download_duplicate_customers_file():
    """
    Generates and allows download of a file containing identified duplicate customer data.

    Functional Requirements Addressed:
    - FR31: The CDP system shall provide a screen for users to download a Duplicate Data File.
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Moengage, Duplicate, Unique, Error).
    - API Endpoint: /exports/duplicate-customers (GET)
    """
    try:
        # The service layer fetches and formats duplicate customer data.
        csv_buffer = ExportService.generate_duplicate_customers_file()
        csv_buffer.seek(0)

        return send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'duplicate_customers_{datetime.date.today().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        print(f"Error generating duplicate customers file: {e}")
        return jsonify({"error": "Failed to generate duplicate customers file", "details": str(e)}), 500

@exports_bp.route('/unique-customers', methods=['GET'])
def download_unique_customers_file():
    """
    Generates and allows download of a file containing unique customer data after deduplication.

    Functional Requirements Addressed:
    - FR32: The CDP system shall provide a screen for users to download a Unique Data File.
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Moengage, Duplicate, Unique, Error).
    - API Endpoint: /exports/unique-customers (GET)
    """
    try:
        # The service layer fetches and formats unique customer data.
        csv_buffer = ExportService.generate_unique_customers_file()
        csv_buffer.seek(0)

        return send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'unique_customers_{datetime.date.today().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        print(f"Error generating unique customers file: {e}")
        return jsonify({"error": "Failed to generate unique customers file", "details": str(e)}), 500

@exports_bp.route('/data-errors', methods=['GET'])
def download_data_errors_file():
    """
    Generates and allows download of an Excel file detailing data validation errors from ingestion processes.

    Functional Requirements Addressed:
    - FR33: The CDP system shall provide a screen for users to download an Error Excel file for data uploads.
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Moengage, Duplicate, Unique, Error).
    - API Endpoint: /exports/data-errors (GET)
    """
    try:
        # The service layer fetches and formats data validation errors into an Excel file.
        # It should return a BytesIO object containing the Excel data.
        excel_buffer = ExportService.generate_data_errors_file()
        excel_buffer.seek(0)

        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'data_errors_{datetime.date.today().strftime("%Y%m%d")}.xlsx'
        )
    except Exception as e:
        print(f"Error generating data errors file: {e}")
        return jsonify({"error": "Failed to generate data errors file", "details": str(e)}), 500