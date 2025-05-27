import click
import csv
import os
import uuid
from datetime import datetime

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

# Assuming these are defined in backend.models and backend.services
# In a real project, these would be imported from their actual paths:
# from backend.models import db, Customer, Offer, IngestionLog
# from backend.services.deduplication_service import DeduplicationService
# from backend.utils.data_validation import validate_offermart_data

# --- Mock/Placeholder components for demonstration within this single file ---
# In a real project, these would be properly defined in their respective files.
# For the purpose of providing a complete, runnable file as requested,
# these simplified definitions are included.

class MockDB:
    """A mock SQLAlchemy db object for demonstration."""
    def __init__(self):
        self.session = self.MockSession()

    class MockSession:
        def add(self, instance):
            current_app.logger.debug(f"MockDB: Added {instance.__class__.__name__} instance.")

        def commit(self):
            current_app.logger.debug("MockDB: Committed transaction.")

        def rollback(self):
            current_app.logger.debug("MockDB: Rolled back transaction.")

        def flush(self):
            current_app.logger.debug("MockDB: Flushed session.")

        def query(self, model):
            return self.MockQuery(model)

    class MockQuery:
        def __init__(self, model):
            self.model = model
            self._filters = []

        def filter(self, *args):
            self._filters.extend(args)
            return self

        def filter_by(self, **kwargs):
            self._filters.append(kwargs)
            return self

        def first(self):
            # In a real scenario, this would query the database.
            # Here, we simulate finding an existing record or None.
            current_app.logger.debug(f"MockDB: Querying {self.model.__name__} with filters: {self._filters}")
            if self.model.__name__ == 'Customer':
                # Simulate finding an existing customer for the first mobile number in mock data
                if any('9876543210' in str(f) for f in self._filters):
                    return Customer(customer_id="mock_customer_1", mobile_number="9876543210")
                return None
            elif self.model.__name__ == 'Offer':
                # Simulate finding an existing offer for OFFER001 for mock_customer_1
                if any('mock_customer_1' in str(f) for f in self._filters) and \
                   any('OFFER001' in str(f) for f in self._filters):
                    return Offer(offer_id="OFFER001", customer_id="mock_customer_1")
                return None
            return None

db = MockDB() # Initialize mock db

# Simplified SQLAlchemy-like models for demonstration
class BaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class Customer(BaseModel):
    __tablename__ = 'customers'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, 'customer_id'):
            self.customer_id = str(uuid.uuid4())
        if not hasattr(self, 'created_at'):
            self.created_at = datetime.utcnow()
        if not hasattr(self, 'updated_at'):
            self.updated_at = datetime.utcnow()

class Offer(BaseModel):
    __tablename__ = 'offers'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, 'created_at'):
            self.created_at = datetime.utcnow()
        if not hasattr(self, 'updated_at'):
            self.updated_at = datetime.utcnow()

class IngestionLog(BaseModel):
    __tablename__ = 'ingestion_logs'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, 'upload_timestamp'):
            self.upload_timestamp = datetime.utcnow()

# Mock for SQLAlchemy's or_
def or_(*args):
    return args # Simply return arguments for mock filter

# backend/services/deduplication_service.py (simplified for this context)
class DeduplicationService:
    @staticmethod
    def process_customer_data(customer_data):
        """
        Handles customer deduplication and creation/update.
        FR3: Deduplicate based on Mobile, Pan, Aadhaar, UCID, or previous loan application number.
        FR4: Across all Consumer Loan products.
        FR5: Deduplicate against 'live book' (Customer 360).
        FR6: Top-up loan offers only within other Top-up offers (this specific logic
             would be more complex and might involve offer type in the query).
        """
        mobile = customer_data.get('mobile_number')
        pan = customer_data.get('pan_number')
        aadhaar = customer_data.get('aadhaar_number')
        ucid = customer_data.get('ucid_number')
        loan_app_num = customer_data.get('loan_application_number')

        # Build a query to find existing customer
        query_filters = []
        if mobile:
            query_filters.append(Customer(mobile_number=mobile)) # Mock filter
        if pan:
            query_filters.append(Customer(pan_number=pan))
        if aadhaar:
            query_filters.append(Customer(aadhaar_number=aadhaar))
        if ucid:
            query_filters.append(Customer(ucid_number=ucid))
        if loan_app_num:
            query_filters.append(Customer(loan_application_number=loan_app_num))

        customer = None
        if query_filters:
            # Use OR to find if any identifier matches
            # In a real SQLAlchemy setup: customer = Customer.query.filter(or_(*query_filters)).first()
            customer = db.session.query(Customer).filter(or_(*query_filters)).first()

        if customer:
            # Update existing customer's details if new data is available
            current_app.logger.info(f"Found existing customer {customer.customer_id}. Updating details.")
            customer.dnd_flag = customer_data.get('dnd_flag', customer.dnd_flag)
            customer.segment = customer_data.get('segment', customer.segment)
            # Update other identifiers if they are new and not conflicting
            if mobile and not getattr(customer, 'mobile_number', None):
                customer.mobile_number = mobile
            if pan and not getattr(customer, 'pan_number', None):
                customer.pan_number = pan
            if aadhaar and not getattr(customer, 'aadhaar_number', None):
                customer.aadhaar_number = aadhaar
            if ucid and not getattr(customer, 'ucid_number', None):
                customer.ucid_number = ucid
            if loan_app_num and not getattr(customer, 'loan_application_number', None):
                customer.loan_application_number = loan_app_num
            db.session.add(customer) # Add to session for update
            return customer.customer_id
        else:
            # Create new customer
            current_app.logger.info("Creating new customer.")
            new_customer = Customer(
                mobile_number=mobile,
                pan_number=pan,
                aadhaar_number=aadhaar,
                ucid_number=ucid,
                loan_application_number=loan_app_num,
                dnd_flag=customer_data.get('dnd_flag', False),
                segment=customer_data.get('segment')
            )
            db.session.add(new_customer)
            db.session.flush() # To get the customer_id before commit
            return new_customer.customer_id

# backend/utils/data_validation.py (simplified for this context)
def validate_offermart_data(row):
    """
    Performs basic column-level validation for Offermart data. (FR1)
    Returns a list of error messages, or empty list if valid.
    """
    errors = []
    required_fields = ['mobile_number', 'offer_id', 'offer_type', 'start_date', 'end_date']
    for field in required_fields:
        if not row.get(field):
            errors.append(f"Missing required field: {field}")

    # Basic format validation for dates and date logic
    start_date_str = row.get('start_date')
    end_date_str = row.get('end_date')
    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append(f"Invalid date format for start_date. Expected YYYY-MM-DD.")
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append(f"Invalid date format for end_date. Expected YYYY-MM-DD.")

    if start_date and end_date and start_date > end_date:
        errors.append("Offer end date cannot be before start date.")

    # Mobile number length/type check
    mobile = row.get('mobile_number')
    if mobile:
        if not mobile.isdigit():
            errors.append("Mobile number must contain only digits.")
        elif len(mobile) not in [10, 12]: # Assuming 10 or 12 digits based on common Indian formats
            errors.append("Mobile number must be 10 or 12 digits long.")

    # Offer status validation (FR16)
    valid_offer_statuses = ['Active', 'Inactive', 'Expired']
    offer_status = row.get('offer_status')
    if offer_status and offer_status not in valid_offer_statuses:
        errors.append(f"Invalid offer_status: '{offer_status}'. Must be one of {valid_offer_statuses}.")

    # Offer type validation (FR17)
    valid_offer_types = ['Fresh', 'Enrich', 'New-old', 'New-new']
    offer_type = row.get('offer_type')
    if offer_type and offer_type not in valid_offer_types:
        errors.append(f"Invalid offer_type: '{offer_type}'. Must be one of {valid_offer_types}.")

    # Propensity validation (FR18) - assuming specific values
    valid_propensities = ['High', 'Medium', 'Low', 'Very High'] # Based on common analytics outputs
    propensity = row.get('propensity')
    if propensity and propensity not in valid_propensities:
        errors.append(f"Invalid propensity: '{propensity}'. Must be one of {valid_propensities}.")

    return errors

# --- End Mock/Placeholder components ---


# Define a path for the staging area. In a real scenario, this would be configured.
# For demonstration, we'll use a mock file path relative to the project root.
# This assumes a 'data' directory at the same level as 'backend'.
OFFERMART_STAGING_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'offermart_daily_feed.csv')


@click.command('ingest-offermart-daily')
def ingest_offermart_daily():
    """
    Performs daily ingestion of customer and offer data from Offermart staging area.
    This task handles FR9, FR1, FR3, FR4, FR5, FR6, FR8, FR16, FR17, FR18, FR19.
    """
    current_app.logger.info("Starting daily Offermart data ingestion task...")

    log_id = str(uuid.uuid4())
    ingestion_status = "FAILED"
    error_description = None
    processed_count = 0
    success_count = 0
    error_count = 0

    try:
        # Simulate reading from a CSV file in the staging area
        if not os.path.exists(OFFERMART_STAGING_PATH):
            current_app.logger.warning(f"Offermart staging file not found: {OFFERMART_STAGING_PATH}. Skipping ingestion.")
            error_description = f"Staging file not found: {OFFERMART_STAGING_PATH}"
            return

        with open(OFFERMART_STAGING_PATH, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data_rows = list(reader)

        if not data_rows:
            current_app.logger.info("No data found in Offermart staging file. Exiting.")
            ingestion_status = "SUCCESS"
            return

        current_app.logger.info(f"Found {len(data_rows)} rows in Offermart staging file.")

        for i, row in enumerate(data_rows):
            processed_count += 1
            try:
                # FR1: Basic column-level validation
                validation_errors = validate_offermart_data(row)
                if validation_errors:
                    error_count += 1
                    current_app.logger.error(f"Validation errors for row {i+1} (Mobile: {row.get('mobile_number')}): {validation_errors}")
                    # In a real system, these errors would be stored for FR34 (Error Excel file)
                    continue

                # Extract customer and offer data
                customer_data = {
                    'mobile_number': row.get('mobile_number'),
                    'pan_number': row.get('pan_number'),
                    'aadhaar_number': row.get('aadhaar_number'),
                    'ucid_number': row.get('ucid_number'),
                    'loan_application_number': row.get('loan_application_number'),
                    'dnd_flag': row.get('dnd_flag', 'FALSE').upper() == 'TRUE',
                    'segment': row.get('segment')
                }

                offer_data = {
                    'offer_id': row.get('offer_id'),
                    'offer_type': row.get('offer_type'),
                    'offer_status': row.get('offer_status'),
                    'propensity': row.get('propensity'),
                    'start_date': datetime.strptime(row['start_date'], '%Y-%m-%d').date() if row.get('start_date') else None,
                    'end_date': datetime.strptime(row['end_date'], '%Y-%m-%d').date() if row.get('end_date') else None,
                    'channel': row.get('channel')
                }

                # FR3, FR4, FR5, FR6: Deduplication logic
                # This service will find an existing customer or create a new one,
                # and return the canonical customer_id.
                # It also handles deduplication against 'live book' (Customer 360) if applicable.
                customer_id = DeduplicationService.process_customer_data(customer_data)

                if not customer_id:
                    error_count += 1
                    current_app.logger.error(f"Failed to process customer for row {i+1} (Mobile: {row.get('mobile_number')}) after deduplication service.")
                    continue

                # FR8, FR16, FR17, FR18, FR19: Process Offer Data
                # Find existing offer for this customer and offer_id
                # In a real SQLAlchemy setup:
                # existing_offer = Offer.query.filter_by(
                #     customer_id=customer_id,
                #     offer_id=offer_data['offer_id']
                # ).first()
                existing_offer = db.session.query(Offer).filter_by(
                    customer_id=customer_id,
                    offer_id=offer_data['offer_id']
                ).first()

                if existing_offer:
                    # FR8: Update old offers with new data
                    current_app.logger.info(f"Updating existing offer {offer_data['offer_id']} for customer {customer_id}.")
                    existing_offer.offer_type = offer_data.get('offer_type', existing_offer.offer_type)
                    existing_offer.offer_status = offer_data.get('offer_status', existing_offer.offer_status)
                    existing_offer.propensity = offer_data.get('propensity', existing_offer.propensity)
                    existing_offer.start_date = offer_data.get('start_date', existing_offer.start_date)
                    existing_offer.end_date = offer_data.get('end_date', existing_offer.end_date)
                    existing_offer.channel = offer_data.get('channel', existing_offer.channel)
                    existing_offer.updated_at = datetime.utcnow()
                else:
                    # Create new offer
                    current_app.logger.info(f"Creating new offer {offer_data['offer_id']} for customer {customer_id}.")
                    new_offer = Offer(
                        offer_id=offer_data['offer_id'],
                        customer_id=customer_id,
                        offer_type=offer_data.get('offer_type'),
                        offer_status=offer_data.get('offer_status', 'Active'), # Default to Active if not provided
                        propensity=offer_data.get('propensity'),
                        start_date=offer_data.get('start_date'),
                        end_date=offer_data.get('end_date'),
                        channel=offer_data.get('channel')
                    )
                    db.session.add(new_offer)

                db.session.commit()
                success_count += 1

            except Exception as e:
                db.session.rollback()
                error_count += 1
                current_app.logger.error(f"Error processing row {i+1} (Mobile: {row.get('mobile_number')}): {e}", exc_info=True)
                # In a real system, you'd store this error in a dedicated error log table
                # or an error file for FR34.

        ingestion_status = "SUCCESS"
        current_app.logger.info(f"Daily Offermart ingestion completed. Processed: {processed_count}, Success: {success_count}, Errors: {error_count}")

    except FileNotFoundError:
        error_description = f"Offermart staging file not found at {OFFERMART_STAGING_PATH}"
        current_app.logger.error(error_description)
    except SQLAlchemyError as e:
        db.session.rollback()
        error_description = f"Database error during ingestion: {e}"
        current_app.logger.error(error_description, exc_info=True)
    except Exception as e:
        error_description = f"An unexpected error occurred during ingestion: {e}"
        current_app.logger.error(error_description, exc_info=True)
    finally:
        # Log the overall ingestion result
        ingestion_log = IngestionLog(
            log_id=log_id,
            file_name=os.path.basename(OFFERMART_STAGING_PATH),
            upload_timestamp=datetime.utcnow(),
            status=ingestion_status,
            error_description=error_description
        )
        db.session.add(ingestion_log)
        db.session.commit()
        current_app.logger.info(f"Ingestion log recorded with status: {ingestion_status}")