from flask import Blueprint, jsonify, request, send_file, current_app
import io
import pandas as pd
from datetime import datetime, timedelta

# Assuming these modules exist for database interaction and business logic
# In a real application, these would contain the actual data retrieval and processing.
# For this exercise, we'll use mock data or simplified logic.
# from app.services.report_service import (
#     generate_moengage_data,
#     get_duplicate_data,
#     get_unique_data,
#     get_error_data,
#     get_daily_tally_report
# )
# from app.utils.errors import APIError, ResourceNotFound

report_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# --- Mock Service Functions (Replace with actual service calls in a real app) ---
def _mock_generate_moengage_data():
    """Mocks fetching data for Moengage file."""
    data = [
        {"customer_id": "cust123", "mobile": "9876543210", "offer_id": "offerA", "campaign_name": "PreapprovedLoan"},
        {"customer_id": "cust124", "mobile": "9876543211", "offer_id": "offerB", "campaign_name": "LoyaltyOffer"},
        {"customer_id": "cust125", "mobile": "9876543212", "offer_id": "offerC", "campaign_name": "TopupLoan"}
    ]
    return pd.DataFrame(data)

def _mock_get_duplicate_data():
    """Mocks fetching duplicate customer data."""
    data = [
        {"customer_id": "cust101", "mobile": "9999900001", "pan": "ABCDE1234F", "duplicate_reason": "Mobile, PAN"},
        {"customer_id": "cust102", "mobile": "9999900001", "pan": "ABCDE1234F", "duplicate_reason": "Mobile, PAN"},
        {"customer_id": "cust103", "mobile": "9999900002", "aadhaar": "123456789012", "duplicate_reason": "Aadhaar"},
        {"customer_id": "cust104", "mobile": "9999900003", "pan": "FGHIJ5678K", "duplicate_reason": "PAN"}
    ]
    return pd.DataFrame(data)

def _mock_get_unique_data():
    """Mocks fetching unique customer data."""
    data = [
        {"customer_id": "cust201", "mobile": "8888800001", "pan": "LMNOP1111Q", "segment": "C1"},
        {"customer_id": "cust202", "mobile": "8888800002", "pan": "RSTUV2222W", "segment": "C2"},
        {"customer_id": "cust203", "mobile": "8888800003", "pan": "XYZAB3333C", "segment": "C1"}
    ]
    return pd.DataFrame(data)

def _mock_get_error_data():
    """Mocks fetching error data from file uploads."""
    data = [
        {"log_id": "log001", "file_name": "upload_20231026.csv", "row_number": 5, "error_desc": "Invalid mobile number format"},
        {"log_id": "log001", "file_name": "upload_20231026.csv", "row_number": 12, "error_desc": "PAN already exists for another customer"},
        {"log_id": "log002", "file_name": "upload_20231027.csv", "row_number": 3, "error_desc": "Missing required field: loan_type"}
    ]
    return pd.DataFrame(data)

def _mock_get_daily_tally_report():
    """Mocks fetching daily tally report data."""
    today = datetime.now().date()
    data = {
        "date": today.strftime("%Y-%m-%d"),
        "total_customers_processed": 1000,
        "new_offers_generated": 500,
        "deduplicated_customers": 150,
        "successful_uploads": 5,
        "failed_uploads": 2
    }
    return data
# --- End Mock Service Functions ---


@report_bp.route('/moengage-file', methods=['GET'])
def download_moengage_file():
    """
    Downloads the Moengage format file in CSV for campaign uploads.
    FR25: The system shall provide a screen for users to download the Moengage File in Excel or CSV format.
    FR39: The system shall provide a front-end utility for LTFS users to download the Moengage format file in .csv format.
    """
    try:
        # In a real app: df = generate_moengage_data()
        df = _mock_generate_moengage_data()

        if df.empty:
            return jsonify({"message": "No Moengage data available for download."}), 404

        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'moengage_campaign_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating Moengage file: {e}")
        return jsonify({"error": "Failed to generate Moengage file.", "details": str(e)}), 500

@report_bp.route('/duplicate-data', methods=['GET'])
def download_duplicate_data():
    """
    Downloads the Duplicate Data File in CSV or Excel format.
    FR26: The system shall provide a screen for users to download the Duplicate Data File in Excel or CSV format.
    Query parameter 'format' can be 'csv' (default) or 'excel'.
    """
    file_format = request.args.get('format', 'csv').lower()

    try:
        # In a real app: df = get_duplicate_data()
        df = _mock_get_duplicate_data()

        if df.empty:
            return jsonify({"message": "No duplicate data available for download."}), 404

        if file_format == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            mimetype = 'text/csv'
            download_name = f'duplicate_customer_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            file_content = io.BytesIO(output.getvalue().encode('utf-8'))
        elif file_format == 'excel':
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_name = f'duplicate_customer_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            file_content = output
        else:
            return jsonify({"error": "Invalid format specified. Use 'csv' or 'excel'."}), 400

        return send_file(
            file_content,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        current_app.logger.error(f"Error generating duplicate data file: {e}")
        return jsonify({"error": "Failed to generate duplicate data file.", "details": str(e)}), 500

@report_bp.route('/unique-data', methods=['GET'])
def download_unique_data():
    """
    Downloads the Unique Data File in CSV or Excel format.
    FR27: The system shall provide a screen for users to download the Unique Data File in Excel or CSV format.
    Query parameter 'format' can be 'csv' (default) or 'excel'.
    """
    file_format = request.args.get('format', 'csv').lower()

    try:
        # In a real app: df = get_unique_data()
        df = _mock_get_unique_data()

        if df.empty:
            return jsonify({"message": "No unique data available for download."}), 404

        if file_format == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            mimetype = 'text/csv'
            download_name = f'unique_customer_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            file_content = io.BytesIO(output.getvalue().encode('utf-8'))
        elif file_format == 'excel':
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_name = f'unique_customer_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            file_content = output
        else:
            return jsonify({"error": "Invalid format specified. Use 'csv' or 'excel'."}), 400

        return send_file(
            file_content,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        current_app.logger.error(f"Error generating unique data file: {e}")
        return jsonify({"error": "Failed to generate unique data file.", "details": str(e)}), 500

@report_bp.route('/error-data', methods=['GET'])
def download_error_data():
    """
    Downloads the Error Excel file for failed data uploads.
    FR28: The system shall provide a screen for users to download the Error Excel file.
    """
    try:
        # In a real app: df = get_error_data()
        df = _mock_get_error_data()

        if df.empty:
            return jsonify({"message": "No error data available for download."}), 404

        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'data_upload_errors_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        current_app.logger.error(f"Error generating error data file: {e}")
        return jsonify({"error": "Failed to generate error data file.", "details": str(e)}), 500

@report_bp.route('/daily-tally', methods=['GET'])
def get_daily_tally():
    """
    Retrieves daily data tally reports for frontend display.
    FR35: The system shall provide a front-end for daily reports for data tally.
    """
    try:
        # In a real app: report_data = get_daily_tally_report()
        report_data = _mock_get_daily_tally_report()

        if not report_data:
            return jsonify({"message": "No daily tally data available for the requested period."}), 404

        return jsonify(report_data), 200
    except Exception as e:
        current_app.logger.error(f"Error retrieving daily tally report: {e}")
        return jsonify({"error": "Failed to retrieve daily tally report.", "details": str(e)}), 500