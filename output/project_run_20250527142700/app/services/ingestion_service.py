import base64
import io
import pandas as pd
from datetime import datetime
from uuid import uuid4
import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_
from flask import current_app # Used for accessing the logger configured with Flask

# Assuming db is initialized in app/extensions.py and models are defined in app.models
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog

class IngestionService:
    """
    Service class responsible for handling all data ingestion processes,
    including real-time API inputs and batch file uploads.
    """

    def __init__(self):
        # Using current_app.logger for consistency with Flask's logging setup
        # This assumes the service is always called within a Flask application context.
        self.logger = current_app.logger if current_app else logging.getLogger(__name__)

    def _validate_data(self, data: dict, required_fields: list) -> bool:
        """
        Performs basic column-level validation for incoming data. (FR1, NFR2)
        """
        for field in required_fields:
            if field not in data or not data[field]:
                self.logger.warning(f"Validation failed: Missing or empty required field '{field}' in data: {data}")
                return False
        return True

    def _find_or_create_customer(self, customer_data: dict) -> tuple[Customer, bool]:
        """
        Finds an existing customer based on provided identifiers (mobile, PAN, Aadhaar, UCID, prev_loan_app_number).
        If no customer is found, a new one is created.
        Handles deduplication logic (FR2, FR3, FR4, FR5).
        Returns the Customer object and a boolean indicating if it was newly created.
        """
        customer = None
        is_new_customer = False

        # Prioritized identifiers for deduplication
        identifiers = {
            'mobile_number': customer_data.get('mobile_number'),
            'pan': customer_data.get('pan'),
            'aadhaar_ref_number': customer_data.get('aadhaar_ref_number'),
            'ucid': customer_data.get('ucid'),
            'previous_loan_app_number': customer_data.get('previous_loan_app_number')
        }

        # Remove None values to avoid querying on non-existent identifiers
        valid_identifiers = {k: v for k, v in identifiers.items() if v}

        if not valid_identifiers:
            self.logger.error("Attempted to find or create customer without any valid identifiers.")
            raise ValueError("At least one customer identifier (mobile, PAN, Aadhaar, UCID, previous loan app number) is required.")

        # Build OR clause for querying
        conditions = []
        for key, value in valid_identifiers.items():
            conditions.append(getattr(Customer, key) == value)

        try:
            customer = db.session.query(Customer).filter(or_(*conditions)).first()

            if customer:
                self.logger.info(f"Found existing customer: {customer.customer_id} using identifiers: {valid_identifiers}")
                # Update existing customer attributes if new data is provided
                for key, value in customer_data.items():
                    if hasattr(customer, key) and value is not None:
                        setattr(customer, key, value)
                customer.updated_at = datetime.now()
            else:
                self.logger.info(f"No existing customer found for identifiers: {valid_identifiers}. Creating new customer.")
                customer = Customer(
                    mobile_number=customer_data.get('mobile_number'),
                    pan=customer_data.get('pan'),
                    aadhaar_ref_number=customer_data.get('aadhaar_ref_number'),
                    ucid=customer_data.get('ucid'),
                    previous_loan_app_number=customer_data.get('previous_loan_app_number'),
                    customer_attributes=customer_data.get('customer_attributes', {}),
                    customer_segment=customer_data.get('customer_segment'),
                    is_dnd=customer_data.get('is_dnd', False)
                )
                db.session.add(customer)
                is_new_customer = True

            db.session.flush() # Use flush to get customer_id if new, before commit
            return customer, is_new_customer

        except IntegrityError as e:
            db.session.rollback()
            self.logger.error(f"Integrity error during customer find/create: {e}")
            raise ValueError(f"Data conflict: A customer with one of the provided unique identifiers already exists. Details: {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Database error during customer find/create: {e}")
            raise RuntimeError(f"Database operation failed: {e}")
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Unexpected error during customer find/create: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}")


    def process_lead_data(self, data: dict) -> dict:
        """
        Receives real-time lead generation data from Insta/E-aggregators and inserts into CDP.
        (FR9, FR10)
        """
        required_fields = ['mobile_number', 'loan_type', 'source_channel']
        if not self._validate_data(data, required_fields):
            return {"status": "error", "message": "Missing required lead data fields."}

        try:
            customer_data = {
                'mobile_number': data.get('mobile_number'),
                'pan': data.get('pan'),
                'previous_loan_app_number': data.get('application_id') # Assuming application_id can be prev_loan_app_number
            }
            customer, _ = self._find_or_create_customer(customer_data)

            # Create a CustomerEvent for lead generation
            event = CustomerEvent(
                customer_id=customer.customer_id,
                event_type='LEAD_GENERATED',
                event_source=data.get('source_channel', 'API'),
                event_details={
                    'loan_type': data.get('loan_type'),
                    'application_id': data.get('application_id')
                }
            )
            db.session.add(event)

            # Potentially create an initial offer record if the lead implies one
            # This logic might need refinement based on specific business rules
            if data.get('offer_id'):
                offer = Offer(
                    customer_id=customer.customer_id,
                    offer_id=data['offer_id'], # Assuming offer_id is provided and unique
                    offer_type='Fresh', # Or 'New-new' based on lead context
                    offer_status='Active',
                    attribution_channel=data.get('source_channel')
                )
                db.session.add(offer)

            db.session.commit()
            self.logger.info(f"Lead processed successfully for customer: {customer.customer_id}")
            return {"status": "success", "message": "Lead processed successfully", "customer_id": str(customer.customer_id)}

        except ValueError as e:
            db.session.rollback()
            self.logger.error(f"Lead processing failed due to validation/data conflict: {e}")
            return {"status": "error", "message": str(e)}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Database error during lead processing: {e}")
            return {"status": "error", "message": "Database error during lead processing."}, 500
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Unexpected error during lead processing: {e}")
            return {"status": "error", "message": "An unexpected error occurred."}, 500

    def process_eligibility_data(self, data: dict) -> dict:
        """
        Receives real-time eligibility check data from Insta/E-aggregators and inserts into CDP.
        (FR9, FR10)
        """
        required_fields = ['mobile_number', 'loan_application_number', 'eligibility_status']
        if not self._validate_data(data, required_fields):
            return {"status": "error", "message": "Missing required eligibility data fields."}

        try:
            customer_data = {'mobile_number': data['mobile_number']}
            customer, _ = self._find_or_create_customer(customer_data) # Ensure customer exists

            # Find or create offer associated with loan_application_number
            offer = db.session.query(Offer).filter_by(
                customer_id=customer.customer_id,
                loan_application_number=data['loan_application_number']
            ).first()

            if not offer:
                # If offer doesn't exist, create a new one. This might happen if eligibility is checked
                # for a new application not yet linked to an existing offer.
                offer = Offer(
                    customer_id=customer.customer_id,
                    loan_application_number=data['loan_application_number'],
                    offer_status='Active', # Default status, might be updated later
                    offer_type='Fresh' # Default type
                )
                db.session.add(offer)
                db.session.flush() # Get offer_id

            # Update offer status based on eligibility
            if data['eligibility_status'].lower() == 'eligible':
                offer.offer_status = 'Active'
            else:
                offer.offer_status = 'Inactive' # Or 'Rejected' if that's a status

            # Create a CustomerEvent for eligibility check
            event = CustomerEvent(
                customer_id=customer.customer_id,
                event_type='ELIGIBILITY_CHECK',
                event_source=data.get('source_channel', 'API'),
                event_details={
                    'loan_application_number': data['loan_application_number'],
                    'eligibility_status': data['eligibility_status'],
                    'offer_id': str(offer.offer_id) if offer else None
                }
            )
            db.session.add(event)

            db.session.commit()
            self.logger.info(f"Eligibility data processed for customer: {customer.customer_id}, LAN: {data['loan_application_number']}")
            return {"status": "success", "message": "Eligibility data processed"}

        except ValueError as e:
            db.session.rollback()
            self.logger.error(f"Eligibility processing failed due to validation/data conflict: {e}")
            return {"status": "error", "message": str(e)}, 400
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Database error during eligibility processing: {e}")
            return {"status": "error", "message": "Database error during eligibility processing."}, 500
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Unexpected error during eligibility processing: {e}")
            return {"status": "error", "message": "An unexpected error occurred."}, 500

    def process_status_data(self, data: dict) -> dict:
        """
        Receives real-time loan application status updates from Insta/E-aggregators and inserts into CDP.
        (FR9, FR10)
        """
        required_fields = ['loan_application_number', 'application_stage']
        if not self._validate_data(data, required_fields):
            return {"status": "error", "message": "Missing required status data fields."}

        try:
            loan_app_number = data['loan_application_number']
            application_stage = data['application_stage']

            # Find the customer associated with the loan application number
            # This assumes a customer and offer should already exist for a status update
            offer = db.session.query(Offer).filter_by(loan_application_number=loan_app_number).first()

            if not offer:
                self.logger.warning(f"Offer not found for loan application number: {loan_app_number}. Cannot process status update.")
                return {"status": "error", "message": f"Offer with loan application number {loan_app_number} not found."}, 404

            customer = db.session.query(Customer).get(offer.customer_id)
            if not customer:
                self.logger.error(f"Customer not found for offer_id: {offer.offer_id}, customer_id: {offer.customer_id}")
                return {"status": "error", "message": "Associated customer not found."}, 404

            # Create a CustomerEvent for the application stage
            event = CustomerEvent(
                customer_id=customer.customer_id,
                event_type=f'APP_STAGE_{application_stage.upper().replace(" ", "_")}',
                event_source=data.get('source_channel', 'LOS'), # LOS or Moengage (FR22)
                event_details={
                    'loan_application_number': loan_app_number,
                    'status_details': data.get('status_details'),
                    'event_timestamp': data.get('event_timestamp', datetime.now().isoformat())
                }
            )
            db.session.add(event)

            # Update offer status based on application stage (FR13, FR38)
            if application_stage.lower() == 'conversion':
                offer.offer_status = 'Converted' # Assuming 'Converted' is a valid status
            elif application_stage.lower() == 'rejected':
                offer.offer_status = 'Rejected'
            elif application_stage.lower() == 'expired': # If LAN validity post journey start is over (FR38)
                offer.offer_status = 'Expired'

            db.session.commit()
            self.logger.info(f"Status updated for LAN: {loan_app_number}, Stage: {application_stage}")
            return {"status": "success", "message": "Status updated"}

        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Database error during status processing: {e}")
            return {"status": "error", "message": "Database error during status processing."}, 500
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Unexpected error during status processing: {e}")
            return {"status": "error", "message": "An unexpected error occurred."}, 500

    def process_customer_upload_file(self, file_content_bytes: bytes, file_type: str, uploaded_by: str) -> dict:
        """
        Processes the uploaded customer details file (Prospect, TW Loyalty, Topup, Employee loans).
        (FR29, FR30, FR31, FR32)
        """
        log_id = uuid4()
        file_name = f"{file_type}_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv" # Placeholder name

        try:
            # Determine file format and read with pandas
            if file_type.lower() == 'csv':
                df = pd.read_csv(io.BytesIO(file_content_bytes))
            elif file_type.lower() in ['excel', 'xlsx']:
                df = pd.read_excel(io.BytesIO(file_content_bytes))
            else:
                raise ValueError("Unsupported file type. Only CSV and Excel are supported.")

            # Expected columns (adjust based on actual file formats from Analytics Team - Ambiguity 4)
            # These are example columns, actual columns would come from the shared templates.
            expected_columns = [
                'mobile_number', 'pan', 'aadhaar_ref_number', 'ucid', 'previous_loan_app_number',
                'offer_type', 'offer_status', 'propensity_flag', 'offer_start_date', 'offer_end_date',
                'customer_segment', 'is_dnd'
            ]

            # Basic column validation (FR1)
            missing_cols = [col for col in expected_columns if col not in df.columns]
            if missing_cols:
                self.logger.warning(f"Uploaded file is missing expected columns: {', '.join(missing_cols)}")
                # Decide if this is a hard error or just a warning. For now, proceed but log.

            success_count = 0
            failed_records = []

            for index, row in df.iterrows():
                record_status = "SUCCESS"
                error_desc = None
                try:
                    # Prepare customer data
                    customer_data = {
                        'mobile_number': str(row.get('mobile_number')) if pd.notna(row.get('mobile_number')) else None,
                        'pan': str(row.get('pan')) if pd.notna(row.get('pan')) else None,
                        'aadhaar_ref_number': str(row.get('aadhaar_ref_number')) if pd.notna(row.get('aadhaar_ref_number')) else None,
                        'ucid': str(row.get('ucid')) if pd.notna(row.get('ucid')) else None,
                        'previous_loan_app_number': str(row.get('previous_loan_app_number')) if pd.notna(row.get('previous_loan_app_number')) else None,
                        'customer_segment': str(row.get('customer_segment')) if pd.notna(row.get('customer_segment')) else None,
                        'is_dnd': bool(row.get('is_dnd')) if pd.notna(row.get('is_dnd')) else False,
                        # Add other customer_attributes if present in the file
                        'customer_attributes': {k: v for k, v in row.items() if k not in expected_columns and pd.notna(v)}
                    }

                    # Basic validation for core identifiers
                    if not (customer_data['mobile_number'] or customer_data['pan'] or customer_data['aadhaar_ref_number'] or customer_data['ucid'] or customer_data['previous_loan_app_number']):
                        raise ValueError("Record must have at least one identifier (mobile, PAN, Aadhaar, UCID, or previous loan app number).")

                    customer, is_new = self._find_or_create_customer(customer_data)

                    # Prepare offer data
                    offer_data = {
                        'offer_type': str(row.get('offer_type')) if pd.notna(row.get('offer_type')) else 'Fresh',
                        'offer_status': str(row.get('offer_status')) if pd.notna(row.get('offer_status')) else 'Active',
                        'propensity_flag': str(row.get('propensity_flag')) if pd.notna(row.get('propensity_flag')) else None,
                        'offer_start_date': pd.to_datetime(row.get('offer_start_date')).date() if pd.notna(row.get('offer_start_date')) else None,
                        'offer_end_date': pd.to_datetime(row.get('offer_end_date')).date() if pd.notna(row.get('offer_end_date')) else None,
                        'loan_application_number': str(row.get('loan_application_number')) if pd.notna(row.get('loan_application_number')) else None,
                        'attribution_channel': str(row.get('attribution_channel')) if pd.notna(row.get('attribution_channel')) else 'File_Upload'
                    }

                    # Create or update offer (FR6, FR15, FR16, FR17)
                    # For simplicity, if a loan_application_number is provided, try to update that offer.
                    # Otherwise, create a new offer. More complex logic for 'update old offers' (FR6)
                    # would involve matching offers based on other criteria.
                    existing_offer = None
                    if offer_data['loan_application_number']:
                        existing_offer = db.session.query(Offer).filter_by(
                            customer_id=customer.customer_id,
                            loan_application_number=offer_data['loan_application_number']
                        ).first()

                    if existing_offer:
                        for key, value in offer_data.items():
                            if hasattr(existing_offer, key) and value is not None:
                                setattr(existing_offer, key, value)
                        existing_offer.updated_at = datetime.now()
                        self.logger.debug(f"Updated offer {existing_offer.offer_id} for customer {customer.customer_id}")
                    else:
                        new_offer = Offer(customer_id=customer.customer_id, **offer_data)
                        db.session.add(new_offer)
                        self.logger.debug(f"Created new offer for customer {customer.customer_id}")

                    db.session.commit() # Commit each row for atomicity, or batch commit for performance
                    success_count += 1

                except ValueError as e:
                    db.session.rollback()
                    record_status = "FAILED"
                    error_desc = f"Validation Error: {e}"
                    self.logger.warning(f"Failed to process row {index + 1}: {error_desc}")
                except IntegrityError as e:
                    db.session.rollback()
                    record_status = "FAILED"
                    error_desc = f"Data Conflict Error: {e.orig.diag.message_detail if e.orig and e.orig.diag else str(e)}"
                    self.logger.warning(f"Failed to process row {index + 1}: {error_desc}")
                except SQLAlchemyError as e:
                    db.session.rollback()
                    record_status = "FAILED"
                    error_desc = f"Database Error: {e}"
                    self.logger.error(f"Failed to process row {index + 1}: {error_desc}")
                except Exception as e:
                    db.session.rollback()
                    record_status = "FAILED"
                    error_desc = f"Unexpected Error: {e}"
                    self.logger.error(f"Failed to process row {index + 1}: {error_desc}")

                if record_status == "FAILED":
                    failed_records.append({
                        'row_number': index + 1,
                        'data': row.to_dict(),
                        'error_desc': error_desc
                    })

            # Log the overall ingestion status (FR31, FR32)
            status = "SUCCESS" if not failed_records else ("PARTIAL" if success_count > 0 else "FAILED")
            error_details = None
            if failed_records:
                error_details = f"{len(failed_records)} records failed. First error: {failed_records[0]['error_desc']}"

            ingestion_log = DataIngestionLog(
                log_id=log_id,
                file_name=file_name,
                upload_timestamp=datetime.now(),
                status=status,
                error_details=error_details,
                uploaded_by=uploaded_by
            )
            db.session.add(ingestion_log)
            db.session.commit()

            self.logger.info(f"File upload processing completed for log_id: {log_id}. Status: {status}, Success: {success_count}, Failed: {len(failed_records)}")

            return {
                "status": status,
                "message": f"File processed. {success_count} records successfully ingested, {len(failed_records)} failed.",
                "log_id": str(log_id),
                "failed_records": failed_records # For generating error file (FR32)
            }

        except ValueError as e:
            self.logger.error(f"File upload failed due to invalid file or format: {e}")
            # Log initial failure for the file itself
            ingestion_log = DataIngestionLog(
                log_id=log_id,
                file_name=file_name,
                upload_timestamp=datetime.now(),
                status="FAILED",
                error_details=f"File processing error: {e}",
                uploaded_by=uploaded_by
            )
            db.session.add(ingestion_log)
            db.session.commit()
            return {"status": "error", "message": str(e), "log_id": str(log_id)}, 400
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during file upload processing: {e}")
            # Log initial failure for the file itself
            ingestion_log = DataIngestionLog(
                log_id=log_id,
                file_name=file_name,
                upload_timestamp=datetime.now(),
                status="FAILED",
                error_details=f"Unexpected error during file processing: {e}",
                uploaded_by=uploaded_by
            )
            db.session.add(ingestion_log)
            db.session.commit()
            return {"status": "error", "message": "An unexpected error occurred during file processing."}, 500