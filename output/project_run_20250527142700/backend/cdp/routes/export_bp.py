from flask import Blueprint, make_response, send_file, jsonify, request
import io
import datetime

# Import the SQLAlchemy db instance from the main application context
# This assumes `db` is initialized in `backend/__init__.py` and made available.
from backend import db
# Import the service layer that handles the actual data retrieval and file generation.
# This promotes separation of concerns, keeping route logic clean.
from backend.services.export_service import ExportService

# Define the Blueprint for export-related routes
export_bp = Blueprint('export_bp', __name__, url_prefix='/exports')

@export_bp.route('/moengage-campaign-file', methods=['GET'])
def download_moengage_campaign_file():
    """
    Generates and allows download of a Moengage-formatted CSV file for eligible customers,
    excluding DND customers.

    Functional Requirements Addressed:
    - FR30: The CDP system shall provide a screen for users to download the Moengage-formatted file (.csv).
    - FR24: The CDP system shall avoid sending offers to DND (Do Not Disturb) customers.
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Moengage).
    """
    try:
        # Delegate the data retrieval and CSV generation to the ExportService.
        # Pass db.session to the service for database interaction.
        csv_buffer = ExportService.generate_moengage_campaign_file(db.session)

        # Create a Flask response to send the file
        response = make_response(send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'moengage_campaign_data_{datetime.date.today().isoformat()}.csv'
        ))
        return response
    except Exception as e:
        # Log the error for debugging purposes (in a real app, use a proper logger)
        print(f"Error generating Moengage campaign file: {e}")
        # Return a JSON error response to the client
        return jsonify({"error": "Failed to generate Moengage campaign file", "details": str(e)}), 500

@export_bp.route('/duplicate-customers', methods=['GET'])
def download_duplicate_customers_file():
    """
    Generates and allows download of a file containing identified duplicate customer data.

    Functional Requirements Addressed:
    - FR31: The CDP system shall provide a screen for users to download a Duplicate Data File.
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Duplicate).
    """
    try:
        # Delegate to ExportService for duplicate customer data CSV generation
        csv_buffer = ExportService.generate_duplicate_customers_file(db.session)

        response = make_response(send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'duplicate_customers_{datetime.date.today().isoformat()}.csv'
        ))
        return response
    except Exception as e:
        print(f"Error generating duplicate customers file: {e}")
        return jsonify({"error": "Failed to generate duplicate customers file", "details": str(e)}), 500

@export_bp.route('/unique-customers', methods=['GET'])
def download_unique_customers_file():
    """
    Generates and allows download of a file containing unique customer data after deduplication.

    Functional Requirements Addressed:
    - FR32: The CDP system shall provide a screen for users to download a Unique Data File.
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Unique).
    """
    try:
        # Delegate to ExportService for unique customer data CSV generation
        csv_buffer = ExportService.generate_unique_customers_file(db.session)

        response = make_response(send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'unique_customers_{datetime.date.today().isoformat()}.csv'
        ))
        return response
    except Exception as e:
        print(f"Error generating unique customers file: {e}")
        return jsonify({"error": "Failed to generate unique customers file", "details": str(e)}), 500

@export_bp.route('/data-errors', methods=['GET'])
def download_data_errors_file():
    """
    Generates and allows download of an Excel file detailing data validation errors from ingestion processes.

    Functional Requirements Addressed:
    - FR33: The CDP system shall provide a screen for users to download an Error Excel file for data uploads.
    - NFR12: The system shall provide a user-friendly front-end utility for downloading various data files (Error).
    """
    try:
        # Delegate to ExportService for Excel generation of data errors
        excel_buffer = ExportService.generate_data_errors_file(db.session)

        response = make_response(send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'data_errors_{datetime.date.today().isoformat()}.xlsx'
        ))
        return response
    except Exception as e:
        print(f"Error generating data errors file: {e}")
        return jsonify({"error": "Failed to generate data errors file", "details": str(e)}), 500