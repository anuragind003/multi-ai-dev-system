import io
import base64
import pandas as pd
import uuid
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Assuming these are defined in your project structure
# In a real application, these would be imported from their respective modules:
# from app.extensions import db
# from app.models import Customer, Offer, DataIngestionLog, CustomerEvent

# --- MOCK IMPORTS AND CLASSES FOR STANDALONE EXECUTION ---
# In a real Flask application, these would be actual ORM models and SQLAlchemy instance.
class MockDB:
    def __init__(self):
        self.session = self

    def add(self, obj):
        pass # Simulate adding to session

    def commit(self):
        pass # Simulate committing transaction

    def rollback(self):
        pass # Simulate rolling back transaction

    def flush(self):
        pass # Simulate flushing to get ID

db = MockDB()

class MockModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if 'log_id' in kwargs:
            self.log_id = kwargs['log_id'] # Ensure log_id is set for DataIngestionLog

class Customer(MockModel):
    pass

class Offer(MockModel):
    pass

class CustomerEvent(MockModel):
    pass

class DataIngestionLog(MockModel):
    pass

# Placeholder for CustomerService. In a real application, this would be a separate,
# fully implemented service responsible for customer-related business logic,
# including deduplication, single profile view, and lead generation.
# For the purpose of making this file runnable, we include a minimal mock.
class CustomerService:
    def process_customer_data_from_upload(self, record_data: dict):
        """
        Mocks the processing of a single customer record from an upload.
        In a real scenario, this would involve:
        - Deduplication (FR3, FR4, FR5) based on mobile, PAN, Aadhaar, UCID, previous loan application number.
        - Creating/updating Customer (FR2) to ensure a single profile view.
        - Generating Lead/Offer (FR30) if applicable.
        - Basic validation (FR1) beyond what's done in file_management.
        - Handling DND customers (FR21) if applicable for lead generation.

        Args:
            record_data (dict): A dictionary representing one row of customer data.
                                Expected keys: mobile_number, pan, aadhaar_ref_number,
                                ucid, previous_loan_app_number, loan_type, source_channel, etc.

        Returns:
            uuid.UUID: The customer_id of the processed customer (either existing or newly created).

        Raises:
            ValueError: If data is invalid or processing fails due to business rules.
            IntegrityError: If a database integrity constraint is violated.
            SQLAlchemyError: For other database-related errors.
        """
        # Simulate basic validation
        if not record_data.get('mobile_number'):
            raise ValueError("Mobile number is missing or invalid for record.")

        # In a real implementation, you would query the database:
        # existing_customer = Customer.query.filter(
        #     (Customer.mobile_number == record_data.get('mobile_number')) |
        #     (Customer.pan == record_data.get('pan')) |
        #     (Customer.aadhaar_ref_number == record_data.get('aadhaar_ref_number')) |
        #     (Customer.ucid == record_data.get('ucid')) |
        #     (Customer.previous_loan_app_number == record_data.get('previous_loan_app_number'))
        # ).first()

        # if existing_customer:
        #     # Apply deduplication logic (FR3, FR4, FR5)
        #     # Update existing_customer with new data if necessary
        #     customer_id = existing_customer.customer_id
        #     current_app.logger.info(f"Deduplicated and updated customer: {customer_id}")
        # else:
        #     # Create new customer (FR2)
        #     new_customer = Customer(
        #         mobile_number=record_data['mobile_number'],
        #         pan=record_data.get('pan'),
        #         aadhaar_ref_number=record_data.get('aadhaar_ref_number'),
        #         ucid=record_data.get('ucid'),
        #         customer_attributes=record_data # Store other attributes as JSONB
        #     )
        #     db.session.add(new_customer)
        #     db.session.flush() # Get ID before commit
        #     customer_id = new_customer.customer_id
        #     current_app.logger.info(f"Created new customer: {customer_id}")

        # Simulate lead generation (FR30) - this might involve creating an Offer or CustomerEvent
        # if record_data.get('loan_type'):
        #     offer = Offer(
        #         customer_id=customer_id,
        #         offer_type='Fresh', # Or based on file_type/logic
        #         offer_status='Active',
        #         # ... other offer details from record_data
        #     )
        #     db.session.add(offer)
        #     current_app.logger.info(f"Generated lead/offer for customer {customer_id}")

        # For this mock, just return a new UUID to simulate success
        return uuid.uuid4()
# --- END MOCK IMPORTS AND CLASSES ---


class FileManagementService:
    def __init__(self):
        self.logger = current_app.logger
        self.customer_service = CustomerService() # Instantiate the customer service

    def process_uploaded_customer_file(self, file_content_base64: str, file_type: str, uploaded_by: str):
        """
        Processes an uploaded customer details file (CSV/Excel), performs validation,
        deduplication, lead generation, and generates success/error reports.

        Args:
            file_content_base64 (str): Base64 encoded content of the file.
            file_type (str): Type of the file ('csv', 'xls', or 'xlsx').
            uploaded_by (str): User who uploaded the file.

        Returns:
            dict: A dictionary containing:
                - 'log_id': UUID of the ingestion log.
                - 'status': 'SUCCESS', 'PARTIAL_SUCCESS', or 'FAILED'.
                - 'message': A descriptive message.
                - 'success_records': List of dictionaries for successfully processed records.
                - 'error_records': List of dictionaries for records that failed processing, including 'error_desc'.
        """
        log_id = uuid.uuid4()
        file_name = f"uploaded_customer_file_{log_id}.{file_type}"
        ingestion_log = DataIngestionLog(
            log_id=log_id,
            file_name=file_name,
            upload_timestamp=datetime.utcnow(),
            status='PROCESSING',
            uploaded_by=uploaded_by
        )
        db.session.add(ingestion_log)
        try:
            db.session.commit() # Commit the log entry immediately
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create initial ingestion log: {e}", exc_info=True)
            db.session.rollback()
            return {
                'log_id': str(log_id),
                'status': 'FAILED',
                'message': f"Failed to initialize file processing: {str(e)}",
                'success_records': [],
                'error_records': []
            }

        success_records = []
        error_records = []
        total_records = 0

        try:
            decoded_content = base64.b64decode(file_content_base64)
            file_stream = io.BytesIO(decoded_content)

            if file_type == 'csv':
                df = pd.read_csv(file_stream)
            elif file_type in ['xls', 'xlsx']:
                df = pd.read_excel(file_stream)
            else:
                raise ValueError("Unsupported file type. Only 'csv', 'xls', 'xlsx' are supported.")

            total_records = len(df)

            # Basic column-level validation (FR1)
            # These are example columns based on BRD and API design.
            # Actual required columns should be confirmed from the missing Excel attachments.
            required_columns = ['mobile_number', 'pan', 'loan_type']
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns in the uploaded file: {', '.join(missing_cols)}")

            for index, row in df.iterrows():
                # Convert pandas NaN to Python None for database compatibility
                record_data = row.where(pd.notnull(row), None).to_dict()
                try:
                    # Call CustomerService to handle customer creation/update, deduplication, and lead generation
                    # This abstracts the complex logic of FR2, FR3, FR4, FR5, FR10, FR30
                    processed_customer_id = self.customer_service.process_customer_data_from_upload(record_data)

                    success_records.append({**record_data, 'customer_id': str(processed_customer_id)})

                except (ValueError, IntegrityError, SQLAlchemyError) as e:
                    self.logger.error(f"Error processing record {index + 1}: {e} - Data: {record_data}")
                    db.session.rollback() # Rollback any partial changes for this record
                    error_records.append({**record_data, 'error_desc': str(e)})
                except Exception as e:
                    self.logger.error(f"Unexpected error processing record {index + 1}: {e} - Data: {record_data}", exc_info=True)
                    db.session.rollback() # Rollback any partial changes for this record
                    error_records.append({**record_data, 'error_desc': f"Unexpected error: {str(e)}"})

            # Update ingestion log status and commit all successful changes
            if not error_records:
                ingestion_log.status = 'SUCCESS'
                ingestion_log.error_details = None
                message = f"Successfully processed {total_records} records."
            elif len(success_records) > 0:
                ingestion_log.status = 'PARTIAL_SUCCESS'
                ingestion_log.error_details = f"{len(error_records)} records failed out of {total_records}."
                message = f"Processed {len(success_records)} records successfully, {len(error_records)} failed."
            else:
                ingestion_log.status = 'FAILED'
                ingestion_log.error_details = f"All {total_records} records failed."
                message = f"All {total_records} records failed to process."

            db.session.commit() # Commit all successful records and the final log status

            return {
                'log_id': str(log_id),
                'status': ingestion_log.status,
                'message': message,
                'success_records': success_records,
                'error_records': error_records
            }

        except ValueError as e:
            self.logger.error(f"File parsing or initial validation error for {file_name}: {e}")
            ingestion_log.status = 'FAILED'
            ingestion_log.error_details = str(e)
            db.session.rollback() # Rollback the initial log entry if parsing failed before any record processing
            db.session.commit() # Commit the failed log entry
            return {
                'log_id': str(log_id),
                'status': 'FAILED',
                'message': f"File processing failed: {str(e)}",
                'success_records': [],
                'error_records': []
            }
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during file processing for {file_name}: {e}", exc_info=True)
            ingestion_log.status = 'FAILED'
            ingestion_log.error_details = f"An unexpected error occurred: {str(e)}"
            db.session.rollback() # Rollback any pending changes
            db.session.commit() # Commit the failed log entry
            return {
                'log_id': str(log_id),
                'status': 'FAILED',
                'message': f"An unexpected error occurred: {str(e)}",
                'success_records': [],
                'error_records': []
            }

    def generate_csv_from_records(self, records: list, filename: str = "data.csv"):
        """Generates a CSV file stream from a list of dictionaries."""
        if not records:
            return io.BytesIO(b""), filename # Return empty CSV if no records
        df = pd.DataFrame(records)
        output = io.BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return output, filename

    def generate_excel_from_records(self, records: list, filename: str = "data.xlsx"):
        """Generates an Excel file stream from a list of dictionaries."""
        if not records:
            return io.BytesIO(b""), filename # Return empty Excel if no records
        df = pd.DataFrame(records)
        output = io.BytesIO()
        # Using ExcelWriter to ensure proper format
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        return output, filename