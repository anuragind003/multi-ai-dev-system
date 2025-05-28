from flask import Blueprint, jsonify, request, send_file, current_app
import io
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date, and_, or_
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign

reports_bp = Blueprint('reports', __name__, url_prefix='/api/v1/reports')

# Helper function to generate file response
def generate_file_response(df, filename, file_format):
    """
    Generates a Flask response to send a file (CSV or Excel) from a pandas DataFrame.
    """
    buffer = io.BytesIO()
    if file_format == 'csv':
        df.to_csv(buffer, index=False, encoding='utf-8')
        mimetype = 'text/csv'
    elif file_format == 'excel':
        # Ensure openpyxl is installed for Excel support
        df.to_excel(buffer, index=False, engine='openpyxl')
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        raise ValueError("Unsupported file format. Must be 'csv' or 'excel'.")

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"{filename}.{file_format}"
    )

@reports_bp.route('/moengage-file', methods=['GET'])
def download_moengage_file():
    """
    FR25, FR39: Downloads the Moengage format file in CSV for campaign uploads.
    Excludes DND customers (FR21).
    """
    try:
        # Query for active offers for non-DND customers
        # This is a simplified query. A real Moengage file might require specific columns
        # and complex joins based on campaign data, customer segments, etc.
        # For now, we'll select basic customer and offer info.
        # Assuming 'Active' offers are relevant for Moengage campaigns.
        moengage_data = db.session.query(
            Customer.mobile_number,
            Customer.customer_segment,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_start_date,
            Offer.offer_end_date,
            Offer.propensity_flag
        ).join(Offer, Customer.customer_id == Offer.customer_id)\
        .filter(
            Customer.is_dnd == False,
            Offer.offer_status == 'Active'
        ).all()

        if not moengage_data:
            return jsonify({"status": "error", "message": "No active offers found for Moengage file generation."}), 404

        # Convert to pandas DataFrame
        df = pd.DataFrame([row._asdict() for row in moengage_data])

        # Rename columns to Moengage friendly names if necessary
        df.rename(columns={
            'mobile_number': 'Customer_Mobile',
            'customer_segment': 'Customer_Segment',
            'offer_id': 'Offer_ID',
            'offer_type': 'Offer_Type',
            'offer_start_date': 'Offer_Start_Date',
            'offer_end_date': 'Offer_End_Date',
            'propensity_flag': 'Propensity_Flag'
        }, inplace=True)

        return generate_file_response(df, "moengage_campaign_data", "csv")

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating Moengage file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating Moengage file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/duplicate-data', methods=['GET'])
def download_duplicate_data_file():
    """
    FR26: Downloads the Duplicate Data File in Excel or CSV format.
    This endpoint assumes that 'duplicate data' refers to records that were identified
    as duplicates during ingestion and potentially logged as errors or rejected.
    It queries DataIngestionLog for records marked as 'FAILED' with a 'duplicate' indication.
    """
    file_format = request.args.get('format', 'csv').lower()
    if file_format not in ['csv', 'excel']:
        return jsonify({"status": "error", "message": "Invalid file format. Must be 'csv' or 'excel'."}), 400

    try:
        # Query DataIngestionLog for failed entries that might indicate duplicates
        # This is a simplified approach. A more robust system might have a dedicated
        # table for identified duplicates or a more sophisticated logging mechanism.
        duplicate_logs = db.session.query(DataIngestionLog).filter(
            DataIngestionLog.status == 'FAILED',
            or_(
                DataIngestionLog.error_details.ilike('%duplicate%'),
                DataIngestionLog.error_details.ilike('%unique constraint%')
            )
        ).order_by(DataIngestionLog.upload_timestamp.desc()).all()

        if not duplicate_logs:
            return jsonify({"status": "error", "message": "No duplicate data records found in logs."}), 404

        df = pd.DataFrame([log.to_dict() for log in duplicate_logs])
        # You might want to parse `error_details` JSONB if it contains structured data
        # For now, just include the raw error_details.

        return generate_file_response(df, "duplicate_data_report", file_format)

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating duplicate data file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating duplicate data file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/unique-data', methods=['GET'])
def download_unique_data_file():
    """
    FR27: Downloads the Unique Data File in Excel or CSV format.
    This endpoint exports all unique customer profiles from the 'customers' table.
    """
    file_format = request.args.get('format', 'csv').lower()
    if file_format not in ['csv', 'excel']:
        return jsonify({"status": "error", "message": "Invalid file format. Must be 'csv' or 'excel'."}), 400

    try:
        # Query all unique customer profiles
        unique_customers = db.session.query(Customer).all()

        if not unique_customers:
            return jsonify({"status": "error", "message": "No unique customer data found."}), 404

        # Convert to pandas DataFrame. Exclude sensitive or large JSONB fields if not needed.
        df = pd.DataFrame([cust.to_dict() for cust in unique_customers])
        # Remove 'customer_attributes' and 'created_at', 'updated_at' if not needed in report
        df = df.drop(columns=['customer_attributes', 'created_at', 'updated_at'], errors='ignore')

        return generate_file_response(df, "unique_customer_data", file_format)

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating unique data file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating unique data file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/error-data', methods=['GET'])
def download_error_excel_file():
    """
    FR28: Downloads the Error Excel file for failed data uploads.
    """
    try:
        # Query DataIngestionLog for all failed entries
        error_logs = db.session.query(DataIngestionLog).filter(
            DataIngestionLog.status == 'FAILED'
        ).order_by(DataIngestionLog.upload_timestamp.desc()).all()

        if not error_logs:
            return jsonify({"status": "error", "message": "No error data found in logs."}), 404

        df = pd.DataFrame([log.to_dict() for log in error_logs])
        # Ensure 'Error Desc' column is present, mapping from 'error_details'
        df.rename(columns={'error_details': 'Error Desc'}, inplace=True)

        return generate_file_response(df, "data_upload_errors", "excel")

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating error file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating error file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/daily-tally', methods=['GET'])
def get_daily_tally_report():
    """
    FR35: Retrieves daily data tally reports for frontend display.
    Allows filtering by start_date and end_date.
    """
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = datetime.now().date() - timedelta(days=7) # Default to last 7 days

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date() # Default to today

        # Ensure end_date includes the full day
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Query for daily tallies
        # This is a simplified aggregation. More complex tallies might involve
        # specific business logic for 'new offers generated', 'deduplicated customers', etc.
        # For now, we'll count based on creation/upload timestamps.

        # Total customers processed (newly created or updated)
        # This is tricky. A customer might be updated multiple times.
        # Let's count distinct customers created/updated within the period.
        # Or, count successful ingestion logs.
        total_customers_processed_query = db.session.query(func.count(func.distinct(DataIngestionLog.log_id)))\
            .filter(
                DataIngestionLog.upload_timestamp >= start_date,
                DataIngestionLog.upload_timestamp <= end_datetime,
                DataIngestionLog.status == 'SUCCESS'
            ).scalar()

        # New offers generated (offers created within the period)
        new_offers_generated_query = db.session.query(func.count(Offer.offer_id))\
            .filter(
                Offer.created_at >= start_date,
                Offer.created_at <= end_datetime
            ).scalar()

        # Deduplicated customers: This is hard to get directly from current schema.
        # It would require a specific log of deduplication events or a 'merged_from_customer_id' field.
        # For now, we'll return a placeholder or count customers that were successfully processed
        # and are now unique. A more accurate metric would be the number of records *removed* due to deduplication.
        # Let's assume for now it refers to the number of unique customers *after* deduplication.
        # This is essentially the count of customers in the system.
        # Or, if we want to show the *impact* of deduplication, we'd need a separate metric.
        # For simplicity, let's count unique customers created/updated in the period.
        deduplicated_customers_query = db.session.query(func.count(func.distinct(Customer.customer_id)))\
            .filter(
                Customer.created_at >= start_date,
                Customer.created_at <= end_datetime
            ).scalar()

        # Total campaigns run
        total_campaigns_query = db.session.query(func.count(Campaign.campaign_id))\
            .filter(
                Campaign.campaign_date >= start_date,
                Campaign.campaign_date <= end_date
            ).scalar()

        report_data = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_customers_processed": total_customers_processed_query or 0,
            "new_offers_generated": new_offers_generated_query or 0,
            "deduplicated_customers_count": deduplicated_customers_query or 0, # Represents unique customers processed in period
            "total_campaigns_run": total_campaigns_query or 0
        }

        return jsonify({"status": "success", "data": report_data}), 200

    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating daily tally report: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating report."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating daily tally report: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500