import uuid
import io
import csv
from datetime import datetime
import pandas as pd
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask import current_app

# Assuming db and models are defined elsewhere and imported.
# In a real Flask application, these would typically come from:
# from backend.src.extensions import db
# from backend.src.models import Customer, Offer, Event, IngestionLog

# For the purpose of providing a complete, runnable file,
# we'll include mock implementations of db and models.
# In a production environment, replace these with actual SQLAlchemy imports.

class MockDB:
    """A mock SQLAlchemy DB object for demonstration purposes."""
    def __init__(self):
        self.session = self # Simulate session being directly on db object

    def add(self, obj):
        current_app.logger.debug(f"MockDB: Adding {obj.__class__.__name__} with ID {getattr(obj, obj.__class__.__name__.lower() + '_id', 'N/A')}")

    def commit(self):
        current_app.logger.debug("MockDB: Committing transaction")

    def rollback(self):
        current_app.logger.debug("MockDB: Rolling back transaction")

    def query(self, model):
        return MockQuery(model)

    def close(self):
        current_app.logger.debug("MockDB: Closing session")

class MockQuery:
    """A mock SQLAlchemy Query object."""
    def __init__(self, model):
        self.model = model
        self._filter_by_args = {}

    def filter_by(self, **kwargs):
        self._filter_by_args.update(kwargs)
        return self

    def first(self):
        """Simulates finding an existing record based on filter_by args."""
        # This is a very basic mock. In a real scenario, you'd query a list/dict of mock data.
        if self.model == MockCustomer:
            # Simulate finding a customer by mobile or PAN for testing
            if self._filter_by_args.get('mobile_number') == '1234567890':
                return MockCustomer(customer_id=str(uuid.uuid4()), mobile_number='1234567890')
            if self._filter_by_args.get('pan_number') == 'ABCDE1234F':
                return MockCustomer(customer_id=str(uuid.uuid4()), pan_number='ABCDE1234F')
            if self._filter_by_args.get('customer_id') and _is_valid_uuid(self._filter_by_args['customer_id']):
                return MockCustomer(customer_id=self._filter_by_args['customer_id'])
        return None

    def all(self):
        return [] # For simplicity, mock all() to return empty list

class MockCustomer:
    """Mock Customer Model."""
    def __init__(self, customer_id=None, mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None, loan_application_number=None, dnd_flag=False, segment=None, created_at=None, updated_at=None):
        self.customer_id = customer_id or str(uuid.uuid4())
        self.mobile_number = mobile_number
        self.pan_number = pan_number
        self.aadhaar_number = aadhaar_number
        self.ucid_number = ucid_number
        self.loan_application_number = loan_application_number
        self.dnd_flag = dnd_flag
        self.segment = segment
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class MockOffer:
    """Mock Offer Model."""
    def __init__(self, offer_id=None, customer_id=None, offer_type=None, offer_status=None, propensity=None, start_date=None, end_date=None, channel=None, created_at=None, updated_at=None):
        self.offer_id = offer_id or str(uuid.uuid4())
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.propensity = propensity
        self.start_date = start_date
        self.end_date = end_date
        self.channel = channel
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

class MockEvent:
    """Mock Event Model."""
    def __init__(self, event_id=None, customer_id=None, event_type=None, event_source=None, event_timestamp=None, event_details=None, created_at=None):
        self.event_id = event_id or str(uuid.uuid4())
        self.customer_id = customer_id
        self.event_type = event_type
        self.event_source = event_source
        self.event_timestamp = event_timestamp or datetime.now()
        self.event_details = event_details or {}
        self.created_at = created_at or datetime.now()

class MockIngestionLog:
    """Mock IngestionLog Model."""
    def __init__(self, log_id=None, file_name=None, upload_timestamp=None, status=None, error_description=None):
        self.log_id = log_id or str(uuid.uuid4())
        self.file_name = file_name
        self.upload_timestamp = upload_timestamp or datetime.now()
        self.status = status
        self.error_description = error_description

# Use the mock objects for the purpose of this file.
# In a real Flask app, these would be actual SQLAlchemy instances and models.
db = MockDB()
Customer = MockCustomer
Offer = MockOffer
Event = MockEvent
IngestionLog = MockIngestionLog

# --- Helper Functions for Validation ---

def _is_valid_mobile(mobile):
    """Basic mobile number validation (10 digits)."""
    return isinstance(mobile, str) and len(mobile) == 10 and mobile.isdigit()

def _is_valid_pan(pan):
    """Basic PAN number validation (10 alphanumeric)."""
    # PAN format: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
    # This is a simplified check.
    return isinstance(pan, str) and len(pan) == 10 and pan.isalnum()

def _is_valid_aadhaar(aadhaar):
    """Basic Aadhaar number validation (12 digits)."""
    return isinstance(aadhaar, str) and len(aadhaar) == 12 and aadhaar.isdigit()

def _is_valid_uuid(uid):
    """Checks if a string is a valid UUID."""
    if not isinstance(uid, str):
        return False
    try:
        uuid.UUID(uid)
        return True
    except ValueError:
        return False

def _validate_common_customer_identifiers(data):
    """Validates at least one key identifier is present and correctly formatted."""
    mobile = data.get('mobile_number')
    pan = data.get('pan_number')
    aadhaar = data.get('aadhaar_number')
    ucid = data.get('ucid_number')
    loan_app_num = data.get('loan_application_number')

    if not (mobile or pan or aadhaar or ucid or loan_app_num):
        return False, "At least one of mobile_number, pan_number, aadhaar_number, ucid_number, or loan_application_number must be provided."

    if mobile is not None and not _is_valid_mobile(str(mobile)):
        return False, "Invalid mobile_number format."
    if pan is not None and not _is_valid_pan(str(pan)):
        return False, "Invalid pan_number format."
    if aadhaar is not None and not _is_valid_aadhaar(str(aadhaar)):
        return False, "Invalid aadhaar_number format."

    return True, ""

def _find_or_create_customer(data):
    """
    Finds an existing customer based on identifiers or creates a new one.
    This is a simplified deduplication logic for ingestion (FR3, FR4, FR5, FR6).
    A more robust deduplication engine would be a separate service.
    """
    customer = None
    # Prioritize unique identifiers for lookup
    if data.get('customer_id') and _is_valid_uuid(data['customer_id']):
        customer = db.session.query(Customer).filter_by(customer_id=data['customer_id']).first()
    if not customer and data.get('mobile_number'):
        customer = db.session.query(Customer).filter_by(mobile_number=str(data['mobile_number'])).first()
    if not customer and data.get('pan_number'):
        customer = db.session.query(Customer).filter_by(pan_number=str(data['pan_number'])).first()
    if not customer and data.get('aadhaar_number'):
        customer = db.session.query(Customer).filter_by(aadhaar_number=str(data['aadhaar_number'])).first()
    if not customer and data.get('ucid_number'):
        customer = db.session.query(Customer).filter_by(ucid_number=str(data['ucid_number'])).first()
    if not customer and data.get('loan_application_number'):
        customer = db.session.query(Customer).filter_by(loan_application_number=str(data['loan_application_number'])).first()

    if customer:
        # Update existing customer with new info if available
        current_app.logger.info(f"Found existing customer: {customer.customer_id}")
        updated = False
        if data.get('mobile_number') and customer.mobile_number is None:
            customer.mobile_number = str(data['mobile_number'])
            updated = True
        if data.get('pan_number') and customer.pan_number is None:
            customer.pan_number = str(data['pan_number'])
            updated = True
        if data.get('aadhaar_number') and customer.aadhaar_number is None:
            customer.aadhaar_number = str(data['aadhaar_number'])
            updated = True
        if data.get('ucid_number') and customer.ucid_number is None:
            customer.ucid_number = str(data['ucid_number'])
            updated = True
        if data.get('loan_application_number') and customer.loan_application_number is None:
            customer.loan_application_number = str(data['loan_application_number'])
            updated = True
        if updated:
            customer.updated_at = datetime.now()
            db.session.add(customer)
        return customer, False # False indicates not newly created
    else:
        # Create new customer
        new_customer_id = str(uuid.uuid4())
        new_customer = Customer(
            customer_id=new_customer_id,
            mobile_number=str(data['mobile_number']) if data.get('mobile_number') else None,
            pan_number=str(data['pan_number']) if data.get('pan_number') else None,
            aadhaar_number=str(data['aadhaar_number']) if data.get('aadhaar_number') else None,
            ucid_number=str(data['ucid_number']) if data.get('ucid_number') else None,
            loan_application_number=str(data['loan_application_number']) if data.get('loan_application_number') else None,
            dnd_flag=bool(data.get('dnd_flag', False)), # Ensure boolean
            segment=data.get('segment')
        )
        db.session.add(new_customer)
        current_app.logger.info(f"Created new customer: {new_customer_id}")
        return new_customer, True # True indicates newly created

# --- Real-time Ingestion Services ---

def ingest_lead_data(data: dict) -> tuple[bool, str, str | None]:
    """
    Ingests real-time lead generation data from Insta/E-aggregators.
    (FR7, FR11, FR12)
    """
    is_valid, error_msg = _validate_common_customer_identifiers(data)
    if not is_valid:
        current_app.logger.warning(f"Lead ingestion validation failed: {error_msg} for data: {data}")
        return False, error_msg, None

    try:
        customer, _ = _find_or_create_customer(data)
        db.session.commit()
        return True, "Lead ingested successfully.", customer.customer_id
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error during lead ingestion: {e}")
        # Attempt to extract more specific error message for unique constraint violations
        detail = getattr(e.orig.diag, 'message_detail', str(e.orig)) if hasattr(e.orig, 'diag') else str(e.orig)
        return False, f"Data integrity error: {detail}", None
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during lead ingestion: {e}")
        return False, f"Database error: {e}", None
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error during lead ingestion: {e}")
        return False, f"An unexpected error occurred: {e}", None
    finally:
        db.session.close()

def ingest_eligibility_data(data: dict) -> tuple[bool, str]:
    """
    Ingests real-time eligibility data from Insta/E-aggregators.
    Updates customer/offer data. (FR7, FR11, FR12)
    """
    customer_id = data.get('customer_id')
    offer_id = data.get('offer_id')
    eligibility_status = data.get('eligibility_status')
    # loan_amount = data.get('loan_amount') # Not directly used in current schema for Offer

    if not (_is_valid_uuid(customer_id) and _is_valid_uuid(offer_id) and eligibility_status):
        return False, "Missing or invalid customer_id, offer_id, or eligibility_status."

    try:
        customer = db.session.query(Customer).filter_by(customer_id=customer_id).first()
        if not customer:
            return False, f"Customer with ID {customer_id} not found."

        offer = db.session.query(Offer).filter_by(offer_id=offer_id, customer_id=customer_id).first()
        if not offer:
            # If offer doesn't exist, create a new one.
            # This assumes eligibility data can create a new offer if it's the first interaction.
            current_app.logger.info(f"Offer {offer_id} not found for customer {customer_id}. Creating a new offer based on eligibility data.")
            offer = Offer(
                offer_id=offer_id,
                customer_id=customer_id,
                offer_status=eligibility_status, # Map eligibility status to offer status
                # Other fields like offer_type, propensity, dates would need to be inferred or provided
                # For now, setting minimal required fields.
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(offer)
        else:
            offer.offer_status = eligibility_status
            offer.updated_at = datetime.now()
            db.session.add(offer)

        db.session.commit()
        return True, "Eligibility updated successfully."
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during eligibility ingestion: {e}")
        return False, f"Database error: {e}"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error during eligibility ingestion: {e}")
        return False, f"An unexpected error occurred: {e}"
    finally:
        db.session.close()

def ingest_status_update(data: dict) -> tuple[bool, str]:
    """
    Ingests real-time application status updates from Insta/E-aggregators or LOS.
    (FR11, FR12, FR22, FR25, FR26)
    """
    loan_application_number = data.get('loan_application_number')
    customer_id = data.get('customer_id')
    current_stage = data.get('current_stage')
    status_timestamp = data.get('status_timestamp')
    event_source = data.get('event_source') # e.g., 'LOS', 'Moengage', 'E-aggregator'

    if not (loan_application_number and _is_valid_uuid(customer_id) and current_stage and status_timestamp and event_source):
        return False, "Missing or invalid loan_application_number, customer_id, current_stage, status_timestamp, or event_source."

    try:
        # Ensure timestamp is datetime object
        if isinstance(status_timestamp, str):
            try:
                status_timestamp = datetime.fromisoformat(status_timestamp)
            except ValueError:
                return False, "Invalid status_timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."

        customer = db.session.query(Customer).filter_by(customer_id=customer_id).first()
        if not customer:
            return False, f"Customer with ID {customer_id} not found."

        # Create an event record
        event = Event(
            event_id=str(uuid.uuid4()),
            customer_id=customer_id,
            event_type=current_stage, # Using current_stage as event_type
            event_source=event_source,
            event_timestamp=status_timestamp,
            event_details={
                "loan_application_number": loan_application_number,
                "current_stage": current_stage,
                "original_payload": data # Store original payload for full traceability
            }
        )
        db.session.add(event)

        # Update customer's loan_application_number if not already set
        if not customer.loan_application_number:
            customer.loan_application_number = loan_application_number
            customer.updated_at = datetime.now()
            db.session.add(customer)

        # FR14: Prevent modification of customer offers with a started loan application journey
        # This service only ingests status. The logic to prevent offer modification
        # would reside in the Offer Management service, which would check the customer's
        # journey status (e.g., by querying events or a status flag on customer/offer).

        db.session.commit()
        return True, "Status updated successfully."
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during status update ingestion: {e}")
        return False, f"Database error: {e}"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error during status update ingestion: {e}")
        return False, f"An unexpected error occurred: {e}"
    finally:
        db.session.close()

# --- File Upload Ingestion Service ---

def process_customer_data_upload(file_stream: io.BytesIO, file_name: str, loan_type: str) -> dict:
    """
    Processes uploaded customer data files (CSV) from the Admin Portal.
    (FR9, FR35, FR36, FR37, FR38)
    """
    log_id = str(uuid.uuid4())
    upload_timestamp = datetime.now()
    success_count = 0
    error_count = 0
    error_rows = []
    # success_rows = [] # Can be used to generate a success file if needed (FR37)

    # Log the start of ingestion
    ingestion_log = IngestionLog(
        log_id=log_id,
        file_name=file_name,
        upload_timestamp=upload_timestamp,
        status="IN_PROGRESS",
        error_description=None
    )
    db.session.add(ingestion_log)
    db.session.commit() # Commit log entry immediately to track processing

    try:
        # Read CSV using pandas for robust parsing and handling various data types
        df = pd.read_csv(file_stream)
        df.columns = [col.lower().strip() for col in df.columns] # Normalize column names

        # Define expected columns and their validation rules
        # This is a simplified example; actual validation would be more detailed per BRD.
        expected_cols = {
            'mobile_number': {'required': False, 'validator': _is_valid_mobile},
            'pan_number': {'required': False, 'validator': _is_valid_pan},
            'aadhaar_number': {'required': False, 'validator': _is_valid_aadhaar},
            'ucid_number': {'required': False, 'validator': lambda x: isinstance(x, str) and len(x) > 0},
            'loan_application_number': {'required': False, 'validator': lambda x: isinstance(x, str) and len(x) > 0},
            'dnd_flag': {'required': False, 'validator': lambda x: str(x).lower() in ['true', 'false', '1', '0', 'yes', 'no', 'y', 'n'] or pd.isna(x)},
            'segment': {'required': False, 'validator': lambda x: isinstance(x, str) and len(x) > 0 or pd.isna(x)},
            'offer_type': {'required': False, 'validator': lambda x: x in ['Fresh', 'Enrich', 'New-old', 'New-new'] or pd.isna(x)},
            'offer_status': {'required': False, 'validator': lambda x: x in ['Active', 'Inactive', 'Expired'] or pd.isna(x)},
            'propensity': {'required': False, 'validator': lambda x: isinstance(x, str) and len(x) > 0 or pd.isna(x)},
            'offer_start_date': {'required': False, 'validator': lambda x: pd.isna(x) or pd.to_datetime(x, errors='coerce') is not pd.NaT},
            'offer_end_date': {'required': False, 'validator': lambda x: pd.isna(x) or pd.to_datetime(x, errors='coerce') is not pd.NaT},
            'channel': {'required': False, 'validator': lambda x: isinstance(x, str) and len(x) > 0 or pd.isna(x)},
        }

        # Check for mandatory columns (at least one identifier)
        identifier_cols = ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number', 'loan_application_number']
        if not any(col in df.columns for col in identifier_cols):
            raise ValueError(f"Uploaded file must contain at least one of {', '.join(identifier_cols)} columns.")

        for index, row in df.iterrows():
            row_data = row.where(pd.notna(row), None).to_dict() # Replace NaN with None
            row_errors = []
            processed_data = {}

            # Basic column-level validation (FR1, NFR3)
            for col, rules in expected_cols.items():
                value = row_data.get(col)

                if value is None and rules['required']:
                    row_errors.append(f"Missing required column: {col}")
                elif value is not None and not rules['validator'](value):
                    row_errors.append(f"Invalid format for column: {col} (value: {value})")
                
                # Type conversion for specific fields
                if col in ['dnd_flag'] and value is not None:
                    processed_data[col] = str(value).lower() in ['true', '1', 'yes', 'y']
                elif col in ['offer_start_date', 'offer_end_date'] and value is not None:
                    try:
                        processed_data[col] = pd.to_datetime(value).date()
                    except ValueError:
                        processed_data[col] = None # Will be caught by validator if required
                else:
                    processed_data[col] = value

            # Specific validation for customer identifiers
            is_valid_identifiers, identifier_error_msg = _validate_common_customer_identifiers(processed_data)
            if not is_valid_identifiers:
                row_errors.append(identifier_error_msg)

            if row_errors:
                error_count += 1
                error_rows.append({
                    "row_number": index + 2, # +2 for 0-indexed and header row
                    "data": row.to_dict(),
                    "error_desc": "; ".join(row_errors)
                })
                continue

            try:
                # Find or create customer (simplified deduplication)
                customer, _ = _find_or_create_customer(processed_data)

                # Create or update offer if offer-related data is present
                # This logic assumes a new offer is created for each row if offer data is provided.
                # A more complex system might update existing offers based on offer_id or other criteria.
                if any(processed_data.get(k) for k in ['offer_type', 'offer_status', 'propensity', 'offer_start_date', 'offer_end_date', 'channel']):
                    offer = Offer(
                        offer_id=str(uuid.uuid4()), # Generate new offer ID for each ingested offer
                        customer_id=customer.customer_id,
                        offer_type=processed_data.get('offer_type'),
                        offer_status=processed_data.get('offer_status', 'Active'), # Default to Active if not provided
                        propensity=processed_data.get('propensity'),
                        start_date=processed_data.get('offer_start_date'),
                        end_date=processed_data.get('offer_end_date'),
                        channel=processed_data.get('channel'),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.session.add(offer)

                db.session.commit()
                success_count += 1
                # success_rows.append(row.to_dict()) # Uncomment if success file generation is needed
            except IntegrityError as e:
                db.session.rollback()
                error_count += 1
                detail = getattr(e.orig.diag, 'message_detail', str(e.orig)) if hasattr(e.orig, 'diag') else str(e.orig)
                error_rows.append({
                    "row_number": index + 2,
                    "data": row.to_dict(),
                    "error_desc": f"Data integrity error: {detail}"
                })
                current_app.logger.warning(f"Integrity error for row {index+2}: {e}")
            except SQLAlchemyError as e:
                db.session.rollback()
                error_count += 1
                error_rows.append({
                    "row_number": index + 2,
                    "data": row.to_dict(),
                    "error_desc": f"Database error: {e}"
                })
                current_app.logger.error(f"Database error for row {index+2}: {e}")
            except Exception as e:
                db.session.rollback()
                error_count += 1
                error_rows.append({
                    "row_number": index + 2,
                    "data": row.to_dict(),
                    "error_desc": f"Unexpected error during row processing: {e}"
                })
                current_app.logger.error(f"Unexpected error for row {index+2}: {e}")

        # Update ingestion log status
        ingestion_log.status = "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS" if success_count > 0 else "FAILED"
        ingestion_log.error_description = f"Processed {success_count} records successfully, {error_count} errors."
        db.session.add(ingestion_log)
        db.session.commit()

        return {
            "log_id": log_id,
            "success_count": success_count,
            "error_count": error_count,
            "error_details": error_rows,
            "status": ingestion_log.status
        }

    except Exception as e:
        db.session.rollback()
        # Update ingestion log for overall file processing failure
        ingestion_log.status = "FAILED"
        ingestion_log.error_description = f"File processing failed: {e}"
        db.session.add(ingestion_log)
        db.session.commit()
        current_app.logger.error(f"Overall file processing failed for {file_name}: {e}")
        return {
            "log_id": log_id,
            "success_count": 0,
            "error_count": len(df) if 'df' in locals() else 0, # If df was created, all rows are errors
            "error_details": [{"row_number": "N/A", "data": {}, "error_desc": f"File processing failed: {e}"}],
            "status": "FAILED"
        }
    finally:
        db.session.close() # Ensure session is closed