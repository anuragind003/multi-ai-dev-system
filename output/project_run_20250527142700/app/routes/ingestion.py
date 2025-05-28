from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.extensions import db
from app.services.ingestion_service import IngestionService

ingestion_bp = Blueprint('ingestion', __name__)

# Initialize the service globally for the blueprint
ingestion_service = IngestionService()

@ingestion_bp.route('/api/leads', methods=['POST'])
def create_lead():
    """
    Receives real-time lead generation data from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("API /api/leads: No JSON data provided.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    try:
        customer_id = ingestion_service.process_lead_data(data)
        return jsonify({
            "status": "success",
            "message": "Lead processed successfully",
            "customer_id": str(customer_id)
        }), 201
    except ValueError as e:
        current_app.logger.error(f"API /api/leads: Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except IntegrityError:
        db.session.rollback()
        current_app.logger.error(
            f"API /api/leads: Data integrity violation for data: {data}"
        )
        return jsonify({
            "status": "error",
            "message": "A customer with the provided unique identifier already exists or data is invalid."
        }), 409
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(
            f"API /api/leads: Database error during lead creation for data: {data}"
        )
        return jsonify({"status": "error", "message": "Database error during lead processing."}), 500
    except Exception as e:
        current_app.logger.exception(
            f"API /api/leads: Unexpected error during lead creation for data: {data}"
        )
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@ingestion_bp.route('/api/eligibility', methods=['POST'])
def process_eligibility():
    """
    Receives real-time eligibility check data from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Eligibility API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("API /api/eligibility: No JSON data provided.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    try:
        ingestion_service.process_eligibility_data(data)
        return jsonify({
            "status": "success",
            "message": "Eligibility data processed"
        }), 200
    except ValueError as e:
        current_app.logger.error(f"API /api/eligibility: Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(
            f"API /api/eligibility: Database error during eligibility processing for data: {data}"
        )
        return jsonify({"status": "error", "message": "Database error during eligibility processing."}), 500
    except Exception as e:
        current_app.logger.exception(
            f"API /api/eligibility: Unexpected error during eligibility processing for data: {data}"
        )
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@ingestion_bp.route('/api/status', methods=['POST'])
def process_status():
    """
    Receives real-time loan application status updates from Insta/E-aggregators and inserts into CDP.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Status API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("API /api/status: No JSON data provided.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    try:
        ingestion_service.process_status_update(data)
        return jsonify({
            "status": "success",
            "message": "Status updated"
        }), 200
    except ValueError as e:
        current_app.logger.error(f"API /api/status: Validation error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(
            f"API /api/status: Database error during status update for data: {data}"
        )
        return jsonify({"status": "error", "message": "Database error during status update."}), 500
    except Exception as e:
        current_app.logger.exception(
            f"API /api/status: Unexpected error during status update for data: {data}"
        )
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500


@ingestion_bp.route('/api/admin/upload/customer-details', methods=['POST'])
def upload_customer_details():
    """
    Uploads customer details file (Prospect, TW Loyalty, Topup, Employee loans) for lead generation via Admin Portal.
    FR29: The Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.
    FR30: The Admin Portal shall generate a lead for customers in the system upon successful file upload.
    FR31: The Admin Portal shall generate a success file upon successful upload of all data.
    FR32: The Admin Portal shall generate an error file with an 'Error Desc' column for failed uploads.
    """
    data = request.get_json()
    if not data:
        current_app.logger.warning("API /api/admin/upload/customer-details: No JSON data provided.")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    file_type = data.get('file_type')
    file_content_base64 = data.get('file_content_base64')
    uploaded_by = data.get('uploaded_by', 'Admin')

    if not file_type or not file_content_base64:
        current_app.logger.error(
            "API /api/admin/upload/customer-details: Missing file_type or file_content_base64."
        )
        return jsonify({
            "status": "error",
            "message": "Missing 'file_type' or 'file_content_base64' in request."
        }), 400

    try:
        log_id = ingestion_service.process_customer_details_file(
            file_type, file_content_base64, uploaded_by
        )
        return jsonify({
            "status": "success",
            "message": "File uploaded, processing initiated",
            "log_id": str(log_id)
        }), 202
    except ValueError as e:
        current_app.logger.error(
            f"API /api/admin/upload/customer-details: Validation error: {e}"
        )
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        current_app.logger.exception(
            f"API /api/admin/upload/customer-details: Unexpected error during file upload for file_type: {file_type}"
        )
        return jsonify({"status": "error", "message": "An unexpected error occurred during file processing."}), 500