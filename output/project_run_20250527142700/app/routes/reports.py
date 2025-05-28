from flask import Blueprint, jsonify, request, send_file, current_app
import io
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date, and_, or_
from sqlalchemy.exc import SQLAlchemyError

# Assuming these modules exist for database interaction and business logic
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign # Import all relevant models

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/moengage-file', methods=['GET'])
def download_moengage_file():
    """
    FR25, FR39: Downloads the Moengage format file in CSV for campaign uploads.
    Filters out DND customers (FR21).
    """
    try:
        # Fetch active offers for non-DND customers.
        # A more robust solution might involve campaign-specific filtering or date range for offers.
        # Example fields for Moengage: mobile_number, offer_id, offer_type, offer_end_date, customer_segment
        
        offers_data = db.session.query(
            Customer.mobile_number,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_end_date,
            Customer.customer_segment,
            Offer.loan_application_number
        ).join(Offer, Customer.customer_id == Offer.customer_id).filter(
            Offer.offer_status == 'Active',
            Customer.is_dnd == False
        ).all()

        if not offers_data:
            return jsonify({"status": "error", "message": "No active offers found for Moengage file generation."}), 404

        # Convert to pandas DataFrame
        df = pd.DataFrame(offers_data, columns=[
            'mobile_number', 'offer_id', 'offer_type', 'offer_end_date', 'customer_segment', 'loan_application_number'
        ])

        # Format offer_end_date for Moengage (e.g., YYYY-MM-DD)
        # Apply formatting only to non-null dates
        df['offer_end_date'] = df['offer_end_date'].apply(
            lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None
        )

        # Create an in-memory CSV file
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        current_app.logger.info("Moengage file generated successfully.")
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'moengage_offers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating Moengage file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating Moengage file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating Moengage file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/duplicate-data', methods=['GET'])
def download_duplicate_data_file():
    """
    FR26: Downloads the Duplicate Data File in Excel or CSV format.
    This report lists records from DataIngestionLog that failed or were partially processed,
    potentially due to duplicate data issues or other errors.
    """
    file_format = request.args.get('format', 'csv').lower() # 'csv' or 'excel'
    
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        query = DataIngestionLog.query.filter(
            or_(
                DataIngestionLog.status == 'FAILED',
                DataIngestionLog.status == 'PARTIAL'
            )
        )

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(DataIngestionLog.upload_timestamp >= start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            query = query.filter(DataIngestionLog.upload_timestamp < end_date + timedelta(days=1))

        duplicate_logs = query.order_by(DataIngestionLog.upload_timestamp.desc()).all()

        if not duplicate_logs:
            return jsonify({"status": "error", "message": "No duplicate/error data logs found for the specified criteria."}), 404

        df = pd.DataFrame([{
            'log_id': str(log.log_id), # Convert UUID to string
            'file_name': log.file_name,
            'upload_timestamp': log.upload_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'status': log.status,
            'error_details': log.error_details,
            'uploaded_by': log.uploaded_by
        } for log in duplicate_logs])

        output = io.BytesIO()
        if file_format == 'excel':
            df.to_excel(output, index=False, engine='xlsxwriter')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_name = f'duplicate_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        else: # default to csv
            df.to_csv(output, index=False)
            mimetype = 'text/csv'
            download_name = f'duplicate_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        output.seek(0)

        current_app.logger.info(f"Duplicate data file generated successfully in {file_format} format.")
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )

    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating duplicate data file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating duplicate data file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating duplicate data file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/unique-data', methods=['GET'])
def download_unique_data_file():
    """
    FR27: Downloads the Unique Data File in Excel or CSV format.
    This report lists all unique customer profiles currently in the system.
    """
    file_format = request.args.get('format', 'csv').lower() # 'csv' or 'excel'
    
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        query = Customer.query

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(Customer.created_at >= start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            query = query.filter(Customer.created_at < end_date + timedelta(days=1))

        unique_customers = query.order_by(Customer.created_at.desc()).all()

        if not unique_customers:
            return jsonify({"status": "error", "message": "No unique customer data found for the specified criteria."}), 404

        df = pd.DataFrame([{
            'customer_id': str(c.customer_id), # Convert UUID to string
            'mobile_number': c.mobile_number,
            'pan': c.pan,
            'aadhaar_ref_number': c.aadhaar_ref_number,
            'ucid': c.ucid,
            'previous_loan_app_number': c.previous_loan_app_number,
            'customer_segment': c.customer_segment,
            'is_dnd': c.is_dnd,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': c.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in unique_customers])

        output = io.BytesIO()
        if file_format == 'excel':
            df.to_excel(output, index=False, engine='xlsxwriter')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_name = f'unique_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        else: # default to csv
            df.to_csv(output, index=False)
            mimetype = 'text/csv'
            download_name = f'unique_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        output.seek(0)

        current_app.logger.info(f"Unique data file generated successfully in {file_format} format.")
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )

    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating unique data file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating unique data file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating unique data file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/error-data', methods=['GET'])
def download_error_excel_file():
    """
    FR28: Downloads the Error Excel file for failed data uploads.
    This report lists entries from DataIngestionLog with 'FAILED' status and their error details.
    """
    file_format = request.args.get('format', 'excel').lower() # 'csv' or 'excel'
    
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        query = DataIngestionLog.query.filter(DataIngestionLog.status == 'FAILED')

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(DataIngestionLog.upload_timestamp >= start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            query = query.filter(DataIngestionLog.upload_timestamp < end_date + timedelta(days=1))

        error_logs = query.order_by(DataIngestionLog.upload_timestamp.desc()).all()

        if not error_logs:
            return jsonify({"status": "error", "message": "No error logs found for the specified criteria."}), 404

        df = pd.DataFrame([{
            'log_id': str(log.log_id), # Convert UUID to string
            'file_name': log.file_name,
            'upload_timestamp': log.upload_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'status': log.status,
            'error_details': log.error_details,
            'uploaded_by': log.uploaded_by
        } for log in error_logs])

        output = io.BytesIO()
        if file_format == 'excel':
            df.to_excel(output, index=False, engine='xlsxwriter')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_name = f'error_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        else: # default to csv
            df.to_csv(output, index=False)
            mimetype = 'text/csv'
            download_name = f'error_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        output.seek(0)

        current_app.logger.info(f"Error data file generated successfully in {file_format} format.")
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )

    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating error data file: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating error data file."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating error data file: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500

@reports_bp.route('/daily-tally', methods=['GET'])
def get_daily_tally_report():
    """
    FR35: Retrieves daily data tally reports for frontend display.
    Metrics: total_customers_processed, new_offers_generated, deduplicated_customers.
    """
    # Get date from query parameters, default to today
    report_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
        
        # Calculate start and end of the day for filtering
        start_of_day = datetime.combine(report_date, datetime.min.time())
        end_of_day = datetime.combine(report_date, datetime.max.time())

        # total_customers_processed: Count of NEW customer records created on this day.
        # This aligns with the idea of "customers processed" resulting in new unique profiles.
        total_customers_processed = db.session.query(Customer).filter(
            Customer.created_at.between(start_of_day, end_of_day)
        ).count()

        # new_offers_generated: Count of offers created on this day.
        new_offers_generated = db.session.query(Offer).filter(
            Offer.created_at.between(start_of_day, end_of_day)
        ).count()

        # deduplicated_customers: This metric is challenging without a dedicated deduplication log.
        # As a pragmatic proxy for MVP, this counts *existing* customer records
        # that were *updated* on this day, implying they underwent some form of processing like enrichment
        # or were affected by a deduplication merge (where an existing record was kept and updated).
        # This excludes customers newly created on the same day.
        deduplicated_customers = db.session.query(Customer).filter(
            Customer.updated_at.between(start_of_day, end_of_day),
            Customer.created_at < start_of_day # Exclude customers created on the same day
        ).count()
        # NOTE: This is a proxy. A more accurate count would require a dedicated deduplication event log
        # or a more granular tracking of deduplication outcomes (e.g., how many incoming records were merged into existing ones).

        report_data = {
            "date": report_date_str,
            "total_customers_processed": total_customers_processed,
            "new_offers_generated": new_offers_generated,
            "deduplicated_customers": deduplicated_customers
        }

        current_app.logger.info(f"Daily tally report generated for {report_date_str}.")
        return jsonify({"status": "success", "data": report_data}), 200

    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error generating daily tally report: {e}")
        return jsonify({"status": "error", "message": "Database error occurred while generating daily tally report."}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating daily tally report: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500