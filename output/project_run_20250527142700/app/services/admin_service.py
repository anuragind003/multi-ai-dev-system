import base64
import io
import uuid
from datetime import datetime
import pandas as pd

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_

from app.extensions import db
from app.models import Customer, Offer, DataIngestionLog

class AdminService:
    """
    Service class for handling administrative tasks, primarily file uploads
    and associated data processing (validation, deduplication, lead generation).
    """

    @staticmethod
    def _validate_customer_data(row: pd.Series) -> tuple[bool, str]:
        """
        Performs basic column-level validation for customer data.
        (FR1: The system shall perform basic column-level validation when moving data from Offermart to CDP.)
        """
        required_fields = ['mobile_number', 'loan_type'] # Minimal required fields for lead generation
        for field in required_fields:
            if pd.isna(row.get(field)) or str(row.get(field)).strip() == '':
                return False, f"Missing required field: {field}"

        # Add more specific validations if needed, e.g., mobile number format, PAN length
        if not str(row['mobile_number']).strip().isdigit() or len(str(row['mobile_number']).strip()) not in [10, 12]:
            return False, "Invalid mobile number format."

        return True, "Validation successful"

    @staticmethod
    def _create_or_update_customer(data: dict) -> tuple[Customer, bool]:
        """
        Handles customer deduplication and creation/update.
        (FR2: single profile view, FR3: deduplication within products, FR4: deduplication against live book)
        Returns the customer object and a boolean indicating if it was a new creation.
        """
        mobile_number = str(data.get('mobile_number')).strip()
        pan = str(data.get('pan')).strip().upper() if data.get('pan') else None
        aadhaar_ref_number = str(data.get('aadhaar_ref_number')).strip() if data.get('aadhaar_ref_number') else None
        ucid = str(data.get('ucid')).strip() if data.get('ucid') else None
        previous_loan_app_number = str(data.get('previous_loan_app_number')).strip() if data.get('previous_loan_app_number') else None

        customer = Customer.query.filter(
            or_(
                Customer.mobile_number == mobile_number,
                (Customer.pan == pan) if pan else False,
                (Customer.aadhaar_ref_number == aadhaar_ref_number) if aadhaar_ref_number else False,
                (Customer.ucid == ucid) if ucid else False,
                (Customer.previous_loan_app_number == previous_loan_app_number) if previous_loan_app_number else False
            )
        ).first()

        is_new_customer = False
        if customer:
            # Update existing customer's attributes if new data is available
            current_app.logger.info(f"Deduplicated: Customer with mobile {mobile_number} already exists. Updating profile.")
            if pan and not customer.pan:
                customer.pan = pan
            if aadhaar_ref_number and not customer.aadhaar_ref_number:
                customer.aadhaar_ref_number = aadhaar_ref_number
            if ucid and not customer.ucid:
                customer.ucid = ucid
            if previous_loan_app_number and not customer.previous_loan_app_number:
                customer.previous_loan_app_number = previous_loan_app_number
            # Update customer_attributes JSONB if needed
            if 'customer_attributes' in data and data['customer_attributes']:
                if customer.customer_attributes:
                    customer.customer_attributes.update(data['customer_attributes'])
                else:
                    customer.customer_attributes = data['customer_attributes']
            customer.updated_at = datetime.now()
        else:
            # Create new customer
            current_app.logger.info(f"Creating new customer for mobile {mobile_number}.")
            customer = Customer(
                mobile_number=mobile_number,
                pan=pan,
                aadhaar_ref_number=aadhaar_ref_number,
                ucid=ucid,
                previous_loan_app_number=previous_loan_app_number,
                customer_attributes=data.get('customer_attributes', {}),
                customer_segment=data.get('customer_segment', None),
                is_dnd=data.get('is_dnd', False)
            )
            db.session.add(customer)
            is_new_customer = True

        return customer, is_new_customer

    @staticmethod
    def process_customer_upload_file(file_content_base64: str, file_type: str, uploaded_by: str) -> dict:
        """
        Processes the uploaded customer details file (Excel/CSV).
        (FR29: Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.)
        (FR30: Admin Portal shall generate a lead for customers in the system upon successful file upload.)
        (FR31: Admin Portal shall generate a success file upon successful upload of all data.)
        (FR32: Admin Portal shall generate an error file with an 'Error Desc' column for failed uploads.)
        """
        logger = current_app.logger
        log_id = uuid.uuid4()
        file_name = f"{file_type}_upload_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx" # Assuming Excel for now

        ingestion_log = DataIngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.now(),
            status='PROCESSING',
            uploaded_by=uploaded_by
        )
        db.session.add(ingestion_log)
        db.session.commit()

        try:
            file_bytes = base64.b64decode(file_content_base64)
            file_stream = io.BytesIO(file_bytes)

            # Determine file type (CSV or Excel) based on content or a header/extension hint
            # For simplicity, assuming Excel for now as FR28 mentions "Error Excel file"
            try:
                df = pd.read_excel(file_stream)
            except Exception:
                # Fallback to CSV if Excel fails
                file_stream.seek(0) # Reset stream position
                df = pd.read_csv(file_stream)

            # Standardize column names to lowercase for easier access
            df.columns = df.columns.str.lower()

            processed_records = []
            error_records = []
            success_count = 0
            failed_count = 0

            for index, row_data in df.iterrows():
                record_status = "SUCCESS"
                error_desc = ""
                customer_id = None
                offer_id = None

                try:
                    # 1. Basic Validation (FR1)
                    is_valid, validation_msg = AdminService._validate_customer_data(row_data)
                    if not is_valid:
                        raise ValueError(validation_msg)

                    customer_data = row_data.to_dict()
                    # Ensure mobile_number is string and stripped
                    customer_data['mobile_number'] = str(customer_data['mobile_number']).strip()

                    # 2. Deduplication and Customer Profile Management (FR2, FR3, FR4)
                    customer, is_new = AdminService._create_or_update_customer(customer_data)
                    db.session.flush() # Flush to get customer.id if new
                    customer_id = customer.customer_id

                    # 3. Generate Lead/Offer (FR30)
                    # Check if an active offer of the same type already exists for this customer
                    existing_offer = Offer.query.filter_by(
                        customer_id=customer.customer_id,
                        offer_type=file_type, # Using file_type as offer_type for simplicity
                        offer_status='Active'
                    ).first()

                    if existing_offer:
                        # Update existing offer if needed, or skip creating a new one
                        current_app.logger.info(f"Customer {customer.customer_id} already has an active {file_type} offer. Skipping new offer creation.")
                        offer_id = existing_offer.offer_id
                        # Optionally update existing offer details if the file provides new info
                        # existing_offer.offer_amount = row_data.get('offer_amount', existing_offer.offer_amount)
                        # existing_offer.updated_at = datetime.now()
                    else:
                        offer = Offer(
                            customer_id=customer.customer_id,
                            offer_type=file_type, # e.g., 'Prospect', 'TW Loyalty', 'Topup', 'Employee loans'
                            offer_status='Active', # FR15
                            offer_start_date=datetime.now().date(),
                            offer_end_date=datetime.now().date() + timedelta(days=30), # Example: 30 days validity
                            propensity_flag=row_data.get('propensity_flag'),
                            attribution_channel=row_data.get('source_channel', 'AdminUpload')
                        )
                        db.session.add(offer)
                        db.session.flush() # Flush to get offer.id
                        offer_id = offer.offer_id
                        current_app.logger.info(f"Generated new offer {offer_id} for customer {customer_id}.")

                    success_count += 1
                    db.session.commit() # Commit after each record for atomicity, or batch commit later

                except (ValueError, SQLAlchemyError, IntegrityError) as e:
                    db.session.rollback() # Rollback any changes for this record
                    record_status = "FAILED"
                    error_desc = str(e)
                    failed_count += 1
                    logger.error(f"Error processing row {index + 1}: {error_desc}")

                # Store results for success/error files (FR31, FR32)
                processed_row = row_data.to_dict()
                processed_row['status'] = record_status
                processed_row['error_desc'] = error_desc
                processed_row['customer_id'] = str(customer_id) if customer_id else None
                processed_row['offer_id'] = str(offer_id) if offer_id else None

                if record_status == "SUCCESS":
                    processed_records.append(processed_row)
                else:
                    error_records.append(processed_row)

            # Update ingestion log status
            if failed_count == 0:
                ingestion_log.status = 'SUCCESS'
            elif success_count > 0:
                ingestion_log.status = 'PARTIAL'
                ingestion_log.error_details = f"{failed_count} records failed out of {len(df)}."
            else:
                ingestion_log.status = 'FAILED'
                ingestion_log.error_details = f"All {len(df)} records failed."

            db.session.commit()

            # In a real scenario, you might save these dataframes to a temporary storage
            # or a dedicated table for error/success logs, which can then be downloaded
            # via the report service (FR28, FR31, FR32).
            # For this MVP, we just return the log ID and counts.
            # The actual file generation for download will be handled by report_service.

            return {
                "log_id": str(log_id),
                "status": ingestion_log.status,
                "message": f"File processed. {success_count} records successful, {failed_count} failed.",
                "success_count": success_count,
                "failed_count": failed_count
            }

        except Exception as e:
            db.session.rollback()
            ingestion_log.status = 'FAILED'
            ingestion_log.error_details = f"File processing failed: {str(e)}"
            db.session.commit()
            logger.exception(f"Critical error during file upload processing for log_id {log_id}")
            raise