import io
import pandas as pd
from datetime import datetime, timedelta
import uuid
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask import current_app
import json

# Assuming these are available from the main app context
# In a real Flask app, these would be imported from app.extensions and app.models
try:
    from app.extensions import db
    from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign
except ImportError:
    # Mock objects for standalone testing or if app context not fully initialized
    # In a production Flask app, this ImportError should not happen if run correctly.
    class MockDB:
        def __init__(self):
            self.session = self
        def add(self, obj): pass
        def commit(self): pass
        def rollback(self): pass
        def query(self, model): return self
        def filter(self, *args): return self
        def first(self): return None
        def all(self): return []
        def delete(self, obj): pass
        def update(self, values): return self
        def execute(self, statement): return self
        def scalars(self): return self
        def all(self): return []

    db = MockDB()

    class MockCustomer:
        def __init__(self, **kwargs):
            self.customer_id = kwargs.get('customer_id', uuid.uuid4())
            self.mobile_number = kwargs.get('mobile_number')
            self.pan = kwargs.get('pan')
            self.aadhaar_ref_number = kwargs.get('aadhaar_ref_number')
            self.ucid = kwargs.get('ucid')
            self.previous_loan_app_number = kwargs.get('previous_loan_app_number')
            self.customer_attributes = kwargs.get('customer_attributes', {})
            self.customer_segment = kwargs.get('customer_segment')
            self.is_dnd = kwargs.get('is_dnd', False)
            self.created_at = kwargs.get('created_at', datetime.utcnow())
            self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        def __repr__(self): return f"<Customer {self.mobile_number}>"

    class MockOffer:
        def __init__(self, **kwargs):
            self.offer_id = kwargs.get('offer_id', uuid.uuid4())
            self.customer_id = kwargs.get('customer_id')
            self.offer_type = kwargs.get('offer_type')
            self.offer_status = kwargs.get('offer_status')
            self.propensity_flag = kwargs.get('propensity_flag')
            self.offer_start_date = kwargs.get('offer_start_date')
            self.offer_end_date = kwargs.get('offer_end_date')
            self.loan_application_number = kwargs.get('loan_application_number')
            self.attribution_channel = kwargs.get('attribution_channel')
            self.created_at = kwargs.get('created_at', datetime.utcnow())
            self.updated_at = kwargs.get('updated_at', datetime.utcnow())

    class MockCustomerEvent:
        def __init__(self, **kwargs):
            self.event_id = kwargs.get('event_id', uuid.uuid4())
            self.customer_id = kwargs.get('customer_id')
            self.event_type = kwargs.get('event_type')
            self.event_source = kwargs.get('event_source')
            self.event_timestamp = kwargs.get('event_timestamp', datetime.utcnow())
            self.event_details = kwargs.get('event_details', {})

    class MockDataIngestionLog:
        def __init__(self, **kwargs):
            self.log_id = kwargs.get('log_id', uuid.uuid4())
            self.file_name = kwargs.get('file_name')
            self.upload_timestamp = kwargs.get('upload_timestamp', datetime.utcnow())
            self.status = kwargs.get('status')
            self.error_details = kwargs.get('error_details')
            self.uploaded_by = kwargs.get('uploaded_by')

    class MockCampaign:
        def __init__(self, **kwargs):
            self.campaign_id = kwargs.get('campaign_id', uuid.uuid4())
            self.campaign_unique_identifier = kwargs.get('campaign_unique_identifier')
            self.campaign_name = kwargs.get('campaign_name')
            self.campaign_date = kwargs.get('campaign_date')
            self.targeted_customers_count = kwargs.get('targeted_customers_count')
            self.attempted_count = kwargs.get('attempted_count')
            self.successfully_sent_count = kwargs.get('successfully_sent_count')
            self.failed_count = kwargs.get('failed_count')
            self.success_rate = kwargs.get('success_rate')
            self.conversion_rate = kwargs.get('conversion_rate')
            self.created_at = kwargs.get('created_at', datetime.utcnow())
            self.updated_at = kwargs.get('updated_at', datetime.utcnow())

    Customer = MockCustomer
    Offer = MockOffer
    CustomerEvent = MockCustomerEvent
    DataIngestionLog = MockDataIngestionLog
    Campaign = MockCampaign

    current_app = type('MockApp', (object,), {'logger': type('MockLogger', (object,), {'info': lambda s, *args: print(f"INFO: {s}"), 'warning': lambda s, *args: print(f"WARNING: {s}"), 'error': lambda s, *args: print(f"ERROR: {s}")})()})()
    print("WARNING: Could not import app.extensions or app.models. Using mock objects.")


class DataProcessingService:
    """
    Service layer for handling core data processing logic including validation,
    deduplication, segmentation, offer management, and report generation.
    """

    def __init__(self):
        pass

    def _validate_customer_data(self, data: dict) -> dict:
        """
        Performs basic column-level validation for customer data. (FR1, NFR2)
        Raises ValueError if validation fails.
        """
        required_fields = ['mobile_number']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Missing required field: {field}")

        if 'mobile_number' in data:
            if not isinstance(data['mobile_number'], str) or not data['mobile_number'].isdigit() or len(data['mobile_number']) < 10:
                raise ValueError("Invalid mobile_number format. Must be a string of at least 10 digits.")
        if 'pan' in data and data['pan'] is not None:
            if not isinstance(data['pan'], str) or len(data['pan']) != 10:
                raise ValueError("Invalid PAN format. Must be a string of 10 characters.")
        if 'aadhaar_ref_number' in data and data['aadhaar_ref_number'] is not None:
            if not isinstance(data['aadhaar_ref_number'], str) or len(data['aadhaar_ref_number']) != 12:
                raise ValueError("Invalid Aadhaar reference number format. Must be a string of 12 digits.")

        # Ensure customer_attributes is a dict if present
        if 'customer_attributes' in data and data['customer_attributes'] is not None:
            if isinstance(data['customer_attributes'], str):
                try:
                    data['customer_attributes'] = json.loads(data['customer_attributes'])
                except json.JSONDecodeError:
                    raise ValueError("customer_attributes must be a valid JSON string or dictionary.")
            elif not isinstance(data['customer_attributes'], dict):
                raise ValueError("customer_attributes must be a dictionary or a JSON string.")

        return data

    def _find_existing_customer(self, identifiers: dict) -> Customer | None:
        """
        Helper to find an existing customer based on various identifiers.
        (FR2, FR3, FR4)
        """
        filters = []
        if identifiers.get('mobile_number'):
            filters.append(Customer.mobile_number == identifiers['mobile_number'])
        if identifiers.get('pan'):
            filters.append(Customer.pan == identifiers['pan'])
        if identifiers.get('aadhaar_ref_number'):
            filters.append(Customer.aadhaar_ref_number == identifiers['aadhaar_ref_number'])
        if identifiers.get('ucid'):
            filters.append(Customer.ucid == identifiers['ucid'])
        if identifiers.get('previous_loan_app_number'):
            filters.append(Customer.previous_loan_app_number == identifiers['previous_loan_app_number'])

        if not filters:
            return None

        return db.session.query(Customer).filter(or_(*filters)).first()

    def process_customer_data(self, customer_data: dict) -> tuple[Customer, bool, str]:
        """
        Processes a single customer record, performing validation, deduplication,
        and creating/updating the customer profile.
        Returns the Customer object, a boolean indicating if it's new, and a status message.
        (FR2, FR3, FR4, FR14, FR19)
        """
        try:
            validated_data = self._validate_customer_data(customer_data)
        except ValueError as e:
            current_app.logger.warning(f"Validation error for customer data: {e} - {customer_data}")
            raise e

        identifiers = {
            'mobile_number': validated_data.get('mobile_number'),
            'pan': validated_data.get('pan'),
            'aadhaar_ref_number': validated_data.get('aadhaar_ref_number'),
            'ucid': validated_data.get('ucid'),
            'previous_loan_app_number': validated_data.get('previous_loan_app_number')
        }

        existing_customer = self._find_existing_customer(identifiers)
        is_new_customer = False
        status_message = "Customer profile updated."

        if existing_customer:
            # Update existing customer's attributes (FR6)
            current_app.logger.info(f"Deduplicated: Customer with mobile {validated_data.get('mobile_number')} already exists. Updating profile.")
            for key, value in validated_data.items():
                if value is not None and hasattr(existing_customer, key):
                    setattr(existing_customer, key, value)
            existing_customer.updated_at = datetime.utcnow()
            customer = existing_customer
        else:
            # Create new customer
            current_app.logger.info(f"New customer: Creating profile for mobile {validated_data.get('mobile_number')}.")
            customer = Customer(**validated_data)
            is_new_customer = True
            status_message = "New customer profile created."

        try:
            db.session.add(customer)
            db.session.flush()
            self._apply_segmentation_logic(customer)
            db.session.commit()
            current_app.logger.info(f"Customer {customer.customer_id} processed successfully.")
            return customer, is_new_customer, status_message
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Database integrity error processing customer {validated_data.get('mobile_number')}: {e}")
            raise ValueError(f"Data conflict: A customer with one of the provided unique identifiers already exists. {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error processing customer {validated_data.get('mobile_number')}: {e}")
            raise RuntimeError(f"Database operation failed: {e}")

    def _apply_segmentation_logic(self, customer: Customer) -> None:
        """
        Applies customer segmentation logic. (FR14, FR19)
        This is a placeholder for actual business logic.
        """
        # Example: Simple segmentation based on some attribute or default
        if customer.customer_attributes and customer.customer_attributes.get('income') and customer.customer_attributes['income'] > 100000:
            customer.customer_segment = 'C1'
        elif customer.customer_attributes and customer.customer_attributes.get('loan_history_count', 0) > 0:
            customer.customer_segment = 'C2'
        else:
            customer.customer_segment = 'C8'
        current_app.logger.info(f"Customer {customer.customer_id} assigned segment: {customer.customer_segment}")

    def apply_attribution_logic(self, customer_id: uuid.UUID) -> None:
        """
        Applies attribution logic to determine which offer/channel prevails. (FR20)
        This is a placeholder for complex business logic.
        """
        offers = db.session.query(Offer).filter_by(customer_id=customer_id, offer_status='Active').all()
        if not offers:
            return

        prevailing_offer = None
        for offer in offers:
            if not prevailing_offer or (offer.created_at and offer.created_at > prevailing_offer.created_at):
                prevailing_offer = offer

        if prevailing_offer:
            current_app.logger.info(f"Attribution: For customer {customer_id}, prevailing offer is {prevailing_offer.offer_id} via {prevailing_offer.attribution_channel}")

    def update_offer_statuses(self) -> None:
        """
        Updates offer statuses based on defined business logic, including expiry.
        (FR13, FR15, FR37, FR38)
        This function is typically run as a scheduled task.
        """
        current_app.logger.info("Starting offer status update and expiry logic...")
        try:
            offers_to_expire_no_journey = db.session.query(Offer).filter(
                Offer.offer_status == 'Active',
                Offer.offer_end_date < datetime.utcnow().date(),
                Offer.loan_application_number.is_(None)
            ).all()

            for offer in offers_to_expire_no_journey:
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.utcnow()
                db.session.add(offer)
                current_app.logger.info(f"Offer {offer.offer_id} (no journey) expired due to end date.")

            offers_to_expire_journey_started = db.session.query(Offer).filter(
                Offer.offer_status == 'Active',
                Offer.loan_application_number.isnot(None),
                Offer.updated_at < datetime.utcnow() - timedelta(days=90)
            ).all()

            for offer in offers_to_expire_journey_started:
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.utcnow()
                db.session.add(offer)
                current_app.logger.info(f"Offer {offer.offer_id} (journey started) expired based on assumed LAN validity.")

            db.session.commit()
            current_app.logger.info("Offer status update and expiry logic completed.")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating offer statuses: {e}")
            raise RuntimeError(f"Failed to update offer statuses: {e}")

    def generate_moengage_file_data(self) -> pd.DataFrame:
        """
        Generates data for the Moengage CSV file. (FR25, FR39)
        Filters out DND customers (FR21).
        """
        current_app.logger.info("Generating Moengage file data...")
        try:
            query = db.session.query(
                Customer.mobile_number,
                Customer.customer_segment,
                Offer.offer_id,
                Offer.offer_type,
                Offer.offer_status,
                Offer.propensity_flag,
                Offer.offer_end_date,
                Offer.loan_application_number,
                Offer.attribution_channel
            ).join(Offer, Customer.customer_id == Offer.customer_id).filter(
                Customer.is_dnd == False,
                Offer.offer_status == 'Active'
            )

            df = pd.read_sql(query.statement, db.session.bind)

            df['MOENGAGE_MOBILE'] = df['mobile_number']
            df['MOENGAGE_OFFER_ID'] = df['offer_id']
            df['MOENGAGE_OFFER_TYPE'] = df['offer_type']
            df['MOENGAGE_SEGMENT'] = df['customer_segment']
            df['MOENGAGE_EXPIRY_DATE'] = df['offer_end_date'].dt.strftime('%Y-%m-%d') if 'offer_end_date' in df.columns and not df['offer_end_date'].empty else None

            moengage_columns = [
                'MOENGAGE_MOBILE', 'MOENGAGE_OFFER_ID', 'MOENGAGE_OFFER_TYPE',
                'MOENGAGE_SEGMENT', 'MOENGAGE_EXPIRY_DATE'
            ]
            df_moengage = df[moengage_columns]
            current_app.logger.info(f"Generated {len(df_moengage)} records for Moengage file.")
            return df_moengage
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error generating Moengage file data: {e}")
            raise RuntimeError(f"Failed to generate Moengage file data: {e}")

    def get_duplicate_data_for_report(self) -> pd.DataFrame:
        """
        Retrieves data identified as duplicates for reporting. (FR26)
        This implementation assumes 'DUPLICATE_PROCESSED' status in DataIngestionLog.
        """
        current_app.logger.info("Retrieving duplicate data for report...")
        try:
            query = db.session.query(DataIngestionLog).filter(
                DataIngestionLog.status == 'DUPLICATE_PROCESSED'
            ).order_by(DataIngestionLog.upload_timestamp.desc()).limit(1000)

            df = pd.read_sql(query.statement, db.session.bind)
            current_app.logger.info(f"Retrieved {len(df)} duplicate records for report.")
            return df
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error retrieving duplicate data for report: {e}")
            raise RuntimeError(f"Failed to retrieve duplicate data: {e}")

    def get_unique_data_for_report(self) -> pd.DataFrame:
        """
        Retrieves unique customer profiles for reporting. (FR27)
        """
        current_app.logger.info("Retrieving unique data for report...")
        try:
            query = db.session.query(
                Customer.customer_id,
                Customer.mobile_number,
                Customer.pan,
                Customer.aadhaar_ref_number,
                Customer.ucid,
                Customer.customer_segment,
                Customer.created_at
            ).order_by(Customer.created_at.desc()).limit(10000)

            df = pd.read_sql(query.statement, db.session.bind)
            current_app.logger.info(f"Retrieved {len(df)} unique customer records for report.")
            return df
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error retrieving unique data for report: {e}")
            raise RuntimeError(f"Failed to retrieve unique data: {e}")

    def get_error_data_for_report(self) -> pd.DataFrame:
        """
        Retrieves error logs from data ingestion for reporting. (FR28)
        """
        current_app.logger.info("Retrieving error data for report...")
        try:
            query = db.session.query(DataIngestionLog).filter(
                or_(DataIngestionLog.status == 'FAILED', DataIngestionLog.status == 'PARTIAL')
            ).order_by(DataIngestionLog.upload_timestamp.desc()).limit(1000)

            df = pd.read_sql(query.statement, db.session.bind)
            current_app.logger.info(f"Retrieved {len(df)} error records for report.")
            return df
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error retrieving error data for report: {e}")
            raise RuntimeError(f"Failed to retrieve error data: {e}")

    def process_uploaded_customer_file(self, file_content: bytes, file_type: str, uploaded_by: str) -> dict:
        """
        Handles the upload and processing of customer details files from the Admin Portal.
        (FR29, FR30, FR31, FR32)
        """
        current_app.logger.info(f"Processing uploaded file of type '{file_type}' by '{uploaded_by}'...")
        log_entry = DataIngestionLog(
            file_name=f"uploaded_customer_file_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_type}",
            upload_timestamp=datetime.utcnow(),
            status='PENDING',
            uploaded_by=uploaded_by
        )
        db.session.add(log_entry)
        db.session.commit()

        try:
            if file_type == 'csv':
                df = pd.read_csv(io.BytesIO(file_content))
            elif file_type in ['xls', 'xlsx']:
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise ValueError("Unsupported file type. Only CSV and Excel (xls, xlsx) are supported.")

            total_records = len(df)
            success_count = 0
            duplicate_count = 0
            error_records = []

            df.columns = df.columns.str.lower()

            if 'mobile_number' not in df.columns:
                raise ValueError("Uploaded file must contain 'mobile_number' column.")

            for index, row in df.iterrows():
                customer_data = row.to_dict()
                customer_data = {k: (None if pd.isna(v) else v) for k, v in customer_data.items()}

                try:
                    customer, is_new, message = self.process_customer_data(customer_data)
                    if is_new:
                        success_count += 1
                    else:
                        duplicate_count += 1
                    current_app.logger.info(f"Row {index+1}: {message} Customer ID: {customer.customer_id}")
                except (ValueError, RuntimeError) as e:
                    error_records.append({'row_index': index + 1, 'data': customer_data, 'error_desc': str(e)})
                    current_app.logger.warning(f"Row {index+1} failed processing: {e}")
                except Exception as e:
                    error_records.append({'row_index': index + 1, 'data': customer_data, 'error_desc': f"Unexpected error: {str(e)}"})
                    current_app.logger.error(f"Row {index+1} failed processing due to unexpected error: {e}", exc_info=True)

            if not error_records:
                log_entry.status = 'SUCCESS'
                log_entry.error_details = None
                current_app.logger.info(f"File '{log_entry.file_name}' processed successfully. Total: {total_records}, New: {success_count}, Duplicates: {duplicate_count}.")
            elif len(error_records) == total_records:
                log_entry.status = 'FAILED'
                log_entry.error_details = f"All {total_records} records failed. First error: {error_records[0]['error_desc']}"
                current_app.logger.error(f"File '{log_entry.file_name}' failed completely. {log_entry.error_details}")
            else:
                log_entry.status = 'PARTIAL'
                log_entry.error_details = f"{len(error_records)} out of {total_records} records failed. See error report for details."
                current_app.logger.warning(f"File '{log_entry.file_name}' processed partially. {log_entry.error_details}")

            db.session.add(log_entry)
            db.session.commit()

            return {
                "log_id": str(log_entry.log_id),
                "status": log_entry.status,
                "total_records": total_records,
                "success_count": success_count,
                "duplicate_count": duplicate_count,
                "failed_count": len(error_records),
                "error_details": error_records if error_records else None
            }

        except ValueError as e:
            db.session.rollback()
            log_entry.status = 'FAILED'
            log_entry.error_details = f"File parsing/initial validation error: {str(e)}"
            db.session.add(log_entry)
            db.session.commit()
            current_app.logger.error(f"File '{log_entry.file_name}' failed due to parsing error: {e}")
            raise e
        except Exception as e:
            db.session.rollback()
            log_entry.status = 'FAILED'
            log_entry.error_details = f"An unexpected error occurred during file processing: {str(e)}"
            db.session.add(log_entry)
            db.session.commit()
            current_app.logger.error(f"File '{log_entry.file_name}' failed due to unexpected error: {e}", exc_info=True)
            raise e

    def get_daily_tally_report(self, report_date: datetime.date) -> dict:
        """
        Retrieves daily data tally reports for frontend display. (FR35)
        This is a simplified example. A real report would aggregate data from various tables.
        """
        current_app.logger.info(f"Generating daily tally report for {report_date}...")
        try:
            start_of_day = datetime.combine(report_date, datetime.min.time())
            end_of_day = datetime.combine(report_date, datetime.max.time())

            total_customers_processed = db.session.query(Customer).filter(
                Customer.created_at >= start_of_day,
                Customer.created_at <= end_of_day
            ).count()

            new_offers_generated = db.session.query(Offer).filter(
                Offer.created_at >= start_of_day,
                Offer.created_at <= end_of_day
            ).count()

            deduplicated_customers = db.session.query(DataIngestionLog).filter(
                DataIngestionLog.upload_timestamp >= start_of_day,
                DataIngestionLog.upload_timestamp <= end_of_day,
                DataIngestionLog.status.in_(['PARTIAL', 'SUCCESS'])
            ).count()

            return {
                "date": report_date.isoformat(),
                "total_customers_processed": total_customers_processed,
                "new_offers_generated": new_offers_generated,
                "deduplicated_customers": deduplicated_customers
            }
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error generating daily tally report for {report_date}: {e}")
            raise RuntimeError(f"Failed to generate daily tally report: {e}")

    def get_customer_single_view(self, customer_id: uuid.UUID) -> dict | None:
        """
        Retrieves a single customer's profile view with associated offers and application stages. (FR2, FR36)
        """
        current_app.logger.info(f"Retrieving single view for customer ID: {customer_id}")
        try:
            customer = db.session.query(Customer).filter_by(customer_id=customer_id).first()
            if not customer:
                return None

            offers = db.session.query(Offer).filter_by(customer_id=customer_id).all()
            events = db.session.query(CustomerEvent).filter_by(customer_id=customer_id).order_by(CustomerEvent.event_timestamp).all()

            customer_data = {
                "customer_id": str(customer.customer_id),
                "mobile_number": customer.mobile_number,
                "pan": customer.pan,
                "aadhaar_ref_number": customer.aadhaar_ref_number,
                "ucid": customer.ucid,
                "previous_loan_app_number": customer.previous_loan_app_number,
                "customer_attributes": customer.customer_attributes,
                "customer_segment": customer.customer_segment,
                "is_dnd": customer.is_dnd,
                "created_at": customer.created_at.isoformat(),
                "updated_at": customer.updated_at.isoformat(),
                "offers": [
                    {
                        "offer_id": str(o.offer_id),
                        "offer_type": o.offer_type,
                        "offer_status": o.offer_status,
                        "propensity_flag": o.propensity_flag,
                        "offer_start_date": o.offer_start_date.isoformat() if o.offer_start_date else None,
                        "offer_end_date": o.offer_end_date.isoformat() if o.offer_end_date else None,
                        "loan_application_number": o.loan_application_number,
                        "attribution_channel": o.attribution_channel,
                        "created_at": o.created_at.isoformat(),
                        "updated_at": o.updated_at.isoformat()
                    } for o in offers
                ],
                "application_stages": [
                    {
                        "event_id": str(e.event_id),
                        "event_type": e.event_type,
                        "event_source": e.event_source,
                        "event_timestamp": e.event_timestamp.isoformat(),
                        "event_details": e.event_details
                    } for e in events
                ]
            }
            return customer_data
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error retrieving single customer view for {customer_id}: {e}")
            raise RuntimeError(f"Failed to retrieve customer view: {e}")