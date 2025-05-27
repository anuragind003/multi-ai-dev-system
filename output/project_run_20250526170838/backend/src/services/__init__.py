import uuid
import datetime
import pandas as pd
import io
import json
from sqlalchemy import create_engine, Column, String, Boolean, Date, DateTime, Integer, Numeric, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError

# --- Database Setup (Minimal for demonstration within this file) ---
# In a real Flask application, this would typically be in a dedicated `database.py` module
# and initialized with the Flask app (e.g., using Flask-SQLAlchemy).
# For the purpose of this single file, we include a basic SQLAlchemy setup.
DATABASE_URL = "postgresql://user:password@host:5432/cdp_db" # Placeholder: Replace with actual DB credentials
Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# --- SQLAlchemy Models (Based on provided DDL) ---
# These models would typically reside in a `models.py` file.
# Given the constraint to provide all code in `__init__.py`, they are defined here.

class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    mobile_number = Column(Text, unique=True)
    pan_number = Column(Text, unique=True)
    aadhaar_number = Column(Text, unique=True)
    ucid_number = Column(Text, unique=True)
    loan_application_number = Column(Text, unique=True)
    dnd_flag = Column(Boolean, default=False)
    segment = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

class Offer(Base):
    __tablename__ = 'offers'
    offer_id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(Text, nullable=False) # In a full ORM, this would be a ForeignKey
    offer_type = Column(Text) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = Column(Text) # 'Active', 'Inactive', 'Expired'
    propensity = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    channel = Column(Text) # For attribution logic
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

class Event(Base):
    __tablename__ = 'events'
    event_id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(Text, nullable=False) # In a full ORM, this would be a ForeignKey
    event_type = Column(Text) # 'SMS_SENT', 'SMS_DELIVERED', 'EKYC_ACHIEVED', 'LOAN_LOGIN', etc.
    event_source = Column(Text) # 'Moengage', 'LOS', 'E-aggregator'
    event_timestamp = Column(DateTime)
    event_details = Column(JSONB) # Flexible storage for event-specific data
    created_at = Column(DateTime, default=datetime.datetime.now)

class CampaignMetric(Base):
    __tablename__ = 'campaign_metrics'
    metric_id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_unique_id = Column(Text, unique=True, nullable=False)
    campaign_name = Column(Text)
    campaign_date = Column(Date)
    attempted_count = Column(Integer)
    sent_success_count = Column(Integer)
    failed_count = Column(Integer)
    conversion_rate = Column(Numeric(5,2))
    created_at = Column(DateTime, default=datetime.datetime.now)

class IngestionLog(Base):
    __tablename__ = 'ingestion_logs'
    log_id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(Text, nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.datetime.now)
    status = Column(Text) # 'SUCCESS', 'FAILED', 'PARTIAL_SUCCESS'
    error_description = Column(Text) # JSON string of errors

# Base.metadata.create_all(engine) # Uncomment to create tables on first run (usually handled by migrations)

# --- Service Classes ---
# Each class encapsulates related business logic and interacts with the database session.

class BaseService:
    """Base class for services to manage database sessions."""
    def __init__(self, session):
        self.session = session

    def _commit_and_close(self):
        """Commits the session and closes it. Handles rollback on error."""
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
        finally:
            self.session.close()

class CustomerService(BaseService):
    """Service for managing customer profiles and deduplication."""

    def get_customer_profile(self, customer_id):
        """FR2, FR40: Retrieves a single customer's profile view with associated offers and journey stages."""
        customer = self.session.query(Customer).filter_by(customer_id=customer_id).first()
        if not customer:
            return None

        offers = self.session.query(Offer).filter_by(customer_id=customer_id).all()
        events = self.session.query(Event).filter_by(customer_id=customer_id).order_by(Event.event_timestamp).all()

        profile = {
            "customer_id": customer.customer_id,
            "mobile_number": customer.mobile_number,
            "pan_number": customer.pan_number,
            "aadhaar_number": customer.aadhaar_number,
            "ucid_number": customer.ucid_number,
            "loan_application_number": customer.loan_application_number,
            "dnd_flag": customer.dnd_flag,
            "segment": customer.segment,
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
            "current_offers": [{
                "offer_id": o.offer_id,
                "offer_type": o.offer_type,
                "offer_status": o.offer_status,
                "propensity": o.propensity,
                "start_date": o.start_date.isoformat() if o.start_date else None,
                "end_date": o.end_date.isoformat() if o.end_date else None,
                "channel": o.channel
            } for o in offers],
            "journey_stages": [{
                "event_type": e.event_type,
                "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
                "source": e.event_source,
                "details": e.event_details
            } for e in events]
        }
        return profile

    def deduplicate_customer_data(self, customer_data):
        """FR3, FR4, FR5, FR6: Performs customer data deduplication.
        Returns (customer_id, is_duplicate_found). If duplicate, returns existing ID.
        If new, creates customer and returns new ID.
        This is a simplified implementation. Real logic would be more robust."""
        mobile = customer_data.get('mobile_number')
        pan = customer_data.get('pan_number')
        aadhaar = customer_data.get('aadhaar_number')
        ucid = customer_data.get('ucid_number')
        loan_app_num = customer_data.get('loan_application_number')

        # Prioritized search for existing customer
        existing_customer = None
        if mobile:
            existing_customer = self.session.query(Customer).filter_by(mobile_number=mobile).first()
        if not existing_customer and pan:
            existing_customer = self.session.query(Customer).filter_by(pan_number=pan).first()
        if not existing_customer and aadhaar:
            existing_customer = self.session.query(Customer).filter_by(aadhaar_number=aadhaar).first()
        if not existing_customer and ucid:
            existing_customer = self.session.query(Customer).filter_by(ucid_number=ucid).first()
        if not existing_customer and loan_app_num:
            existing_customer = self.session.query(Customer).filter_by(loan_application_number=loan_app_num).first()

        if existing_customer:
            # Update existing customer with any new non-null data from `customer_data`
            # This is a basic merge. A real system would have complex merge rules.
            updated = False
            if mobile and not existing_customer.mobile_number:
                existing_customer.mobile_number = mobile; updated = True
            if pan and not existing_customer.pan_number:
                existing_customer.pan_number = pan; updated = True
            if aadhaar and not existing_customer.aadhaar_number:
                existing_customer.aadhaar_number = aadhaar; updated = True
            if ucid and not existing_customer.ucid_number:
                existing_customer.ucid_number = ucid; updated = True
            if loan_app_num and not existing_customer.loan_application_number:
                existing_customer.loan_application_number = loan_app_num; updated = True
            if customer_data.get('dnd_flag') is not None and existing_customer.dnd_flag != customer_data['dnd_flag']:
                existing_customer.dnd_flag = customer_data['dnd_flag']; updated = True
            if customer_data.get('segment') and not existing_customer.segment:
                existing_customer.segment = customer_data['segment']; updated = True

            if updated:
                self.session.add(existing_customer)
                # Note: Commit is handled by the calling service (e.g., IngestionService) for batch operations.
                # For single API calls, it would be committed immediately.
            return existing_customer.customer_id, True # (customer_id, is_duplicate)
        else:
            new_customer = Customer(
                mobile_number=mobile,
                pan_number=pan,
                aadhaar_number=aadhaar,
                ucid_number=ucid,
                loan_application_number=loan_app_num,
                dnd_flag=customer_data.get('dnd_flag', False),
                segment=customer_data.get('segment')
            )
            self.session.add(new_customer)
            self.session.flush() # To get the customer_id before commit
            return new_customer.customer_id, False

    def update_customer_dnd_status(self, customer_id, dnd_flag):
        """Updates the DND flag for a customer (implied by FR23)."""
        customer = self.session.query(Customer).filter_by(customer_id=customer_id).first()
        if customer:
            customer.dnd_flag = dnd_flag
            self.session.add(customer)
            self._commit_and_close()
            return True
        return False

    def get_unique_customers_file(self):
        """FR33: Generates a CSV file of unique customer records."""
        customers = self.session.query(Customer).all()
        df = pd.DataFrame([{
            "customer_id": c.customer_id,
            "mobile_number": c.mobile_number,
            "pan_number": c.pan_number,
            "aadhaar_number": c.aadhaar_number,
            "ucid_number": c.ucid_number,
            "loan_application_number": c.loan_application_number,
            "dnd_flag": c.dnd_flag,
            "segment": c.segment,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        } for c in customers])
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    def get_duplicate_customers_file(self):
        """FR32: Generates a CSV file of identified duplicate customer records.
        This requires a separate mechanism to log duplicates before merging/discarding.
        For this simplified model, it returns an empty file as duplicates are merged."""
        # In a real system, this would query a dedicated 'duplicate_log' table
        # or analyze customer records that were merged.
        df = pd.DataFrame(columns=["original_id", "duplicate_id", "reason", "merged_to_id", "timestamp"])
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

class OfferService(BaseService):
    """Service for managing offers and their lifecycle."""

    def update_offer_status(self, offer_id, status):
        """FR16: Updates the status of an offer."""
        offer = self.session.query(Offer).filter_by(offer_id=offer_id).first()
        if offer:
            offer.offer_status = status
            offer.updated_at = datetime.datetime.now()
            self.session.add(offer)
            self._commit_and_close()
            return True
        return False

    def get_offer_history(self, customer_id, months=6):
        """FR19: Retrieves offer history for a customer for the past N months."""
        six_months_ago = datetime.datetime.now() - datetime.timedelta(days=months * 30)
        offers = self.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.created_at >= six_months_ago
        ).order_by(Offer.created_at.desc()).all()
        return [{
            "offer_id": o.offer_id,
            "offer_type": o.offer_type,
            "offer_status": o.offer_status,
            "propensity": o.propensity,
            "start_date": o.start_date.isoformat() if o.start_date else None,
            "end_date": o.end_date.isoformat() if o.end_date else None,
            "channel": o.channel,
            "created_at": o.created_at.isoformat()
        } for o in offers]

    def apply_attribution_logic(self, customer_id, new_offer_data):
        """FR21: Applies attribution logic to determine which offer prevails.
        This is a simplified placeholder. Real logic would be complex."""
        existing_active_offers = self.session.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active',
            Offer.end_date >= datetime.date.today()
        ).all()

        new_offer_type = new_offer_data.get('offer_type', 'Fresh')
        new_offer_channel = new_offer_data.get('channel')

        # Example simplified logic: If customer has an active offer, new one might be 'Enrich'
        if existing_active_offers and new_offer_type == 'Fresh':
            new_offer_type = 'Enrich' # Or 'New-old' based on FR17

        offer = Offer(
            customer_id=customer_id,
            offer_type=new_offer_type,
            offer_status='Active', # Default status for new offers
            propensity=new_offer_data.get('propensity'),
            start_date=new_offer_data.get('start_date'),
            end_date=new_offer_data.get('end_date'),
            channel=new_offer_channel
        )
        self.session.add(offer)
        self.session.flush() # To get offer_id before commit
        return offer.offer_id

    def replenish_expired_offers(self):
        """FR42: Scheduled task to check for and replenish new offers for non-journey started customers."""
        today = datetime.date.today()
        # Find offers that are active but have passed their end_date
        expired_offers_to_update = self.session.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.end_date < today
        ).all()

        replenished_count = 0
        for offer in expired_offers_to_update:
            # Mark old offer as expired
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.datetime.now()
            self.session.add(offer)

            # Check if customer has an ongoing loan application journey (FR14)
            # This requires checking the Customer's loan_application_number and its status via events.
            # For simplicity, we assume no journey if loan_application_number is null or old.
            customer = self.session.query(Customer).filter_by(customer_id=offer.customer_id).first()
            if customer and not customer.loan_application_number: # Simplified check for 'non-journey started'
                # Generate a new offer (simplified)
                new_offer = Offer(
                    customer_id=offer.customer_id,
                    offer_type='Fresh', # Or 'New-new' based on FR17
                    offer_status='Active',
                    propensity='Medium', # Placeholder
                    start_date=today,
                    end_date=today + datetime.timedelta(days=30), # 30 days validity
                    channel='System_Replenish'
                )
                self.session.add(new_offer)
                replenished_count += 1
        self._commit_and_close()
        return replenished_count

    def mark_offers_expired_by_lan_validity(self):
        """FR43: Marks offers as expired for journey started customers whose LAN validity is over.
        This is a placeholder as specific LAN validity rules are not defined (Question 16)."""
        expired_count = 0
        # Logic would involve:
        # 1. Identifying customers with an active `loan_application_number`.
        # 2. Checking the validity period of that LAN (e.g., from events or a separate table).
        # 3. If LAN is expired/rejected, find associated active offers and mark them 'Expired'.
        # This is a complex business rule that needs more data context.
        # For now, this method performs no action.
        # Example:
        # customers_with_active_lan = self.session.query(Customer).filter(Customer.loan_application_number.isnot(None)).all()
        # for customer in customers_with_active_lan:
        #     # Check LAN validity/status (e.g., from LOS events)
        #     # If LAN is expired/rejected:
        #     offers_to_expire = self.session.query(Offer).filter(
        #         Offer.customer_id == customer.customer_id,
        #         Offer.offer_status == 'Active'
        #     ).all()
        #     for offer in offers_to_expire:
        #         offer.offer_status = 'Expired'
        #         self.session.add(offer)
        #         expired_count += 1
        # self._commit_and_close()
        return expired_count

class IngestionService(BaseService):
    """Service for handling data ingestion from various sources."""

    def __init__(self, session, customer_service_instance, offer_service_instance):
        super().__init__(session)
        self.customer_service = customer_service_instance
        self.offer_service = offer_service_instance

    def _validate_data_row(self, row, source_type):
        """FR1, NFR3: Performs basic column-level validation."""
        errors = []
        # Example validations (more detailed validations would come from 'Dataset_Validations_UnifiedCL_v1.1.xlsx')
        if not row.get('mobile_number') or not str(row['mobile_number']).isdigit() or len(str(row['mobile_number'])) != 10:
            errors.append("Invalid or missing mobile_number (must be 10 digits)")
        if source_type in ['Prospect', 'TW Loyalty', 'Offermart'] and not row.get('pan_number'):
            errors.append("PAN number is required for this data source/loan type")
        # Add more validations as per business rules
        return errors

    def process_offermart_data(self, data_csv_content):
        """FR9: Processes daily batch data from Offermart."""
        df = pd.read_csv(io.StringIO(data_csv_content))
        success_count = 0
        error_records = []

        for index, row in df.iterrows():
            row_dict = row.to_dict()
            errors = self._validate_data_row(row_dict, 'Offermart')
            if errors:
                error_records.append({"row_data": row_dict, "errors": errors})
                continue

            try:
                customer_id, is_duplicate = self.customer_service.deduplicate_customer_data(row_dict)
                
                # FR8: Update old offers in Analytics Offermart with new data received from CDP
                # This implies updating existing offers or creating new ones based on business rules.
                # For simplicity, we'll create a new offer if it's a new offer_id, or update if existing.
                # A more robust solution would involve checking offer_id or other unique offer identifiers.
                
                offer_data = {
                    "customer_id": customer_id,
                    "offer_type": row_dict.get('offer_type', 'Fresh'),
                    "propensity": row_dict.get('propensity'),
                    "start_date": pd.to_datetime(row_dict.get('start_date')).date() if pd.notna(row_dict.get('start_date')) else None,
                    "end_date": pd.to_datetime(row_dict.get('end_date')).date() if pd.notna(row_dict.get('end_date')) else None,
                    "channel": row_dict.get('channel', 'Offermart'),
                    "offer_status": row_dict.get('offer_status', 'Active') # Assume active unless specified
                }
                
                # If an offer_id is provided and exists, update it. Otherwise, create new.
                existing_offer_id = row_dict.get('offer_id')
                if existing_offer_id:
                    existing_offer = self.session.query(Offer).filter_by(offer_id=existing_offer_id, customer_id=customer_id).first()
                    if existing_offer:
                        for key, value in offer_data.items():
                            setattr(existing_offer, key, value)
                        existing_offer.updated_at = datetime.datetime.now()
                        self.session.add(existing_offer)
                    else: # Offer ID provided but not found, treat as new
                        self.session.add(Offer(offer_id=existing_offer_id, **offer_data))
                else: # No offer_id provided, create new
                    self.session.add(Offer(**offer_data))
                
                success_count += 1
            except Exception as e:
                error_records.append({"row_data": row_dict, "errors": [str(e)]})
        self._commit_and_close() # Commit all changes at once for batch
        return success_count, error_records

    def process_realtime_lead(self, data):
        """FR7, FR11, FR12: Receives real-time lead generation data from Insta/E-aggregators."""
        errors = self._validate_data_row(data, 'Realtime_Lead')
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")

        customer_id, is_duplicate = self.customer_service.deduplicate_customer_data(data)
        
        # Create a new offer for the lead using attribution logic
        offer_id = self.offer_service.apply_attribution_logic(customer_id, {
            "offer_type": "Fresh", # Assuming new leads get 'Fresh' offers
            "propensity": data.get('propensity', 'High'), # Propensity from API or default
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=30), # Example validity
            "channel": data.get('source_channel', 'API_Lead')
        })
        self._commit_and_close()
        return customer_id, offer_id

    def process_realtime_eligibility(self, data):
        """FR7, FR11, FR12: Receives real-time eligibility data from Insta/E-aggregators."""
        customer_id = data.get('customer_id')
        offer_id = data.get('offer_id')
        eligibility_status = data.get('eligibility_status')
        loan_amount = data.get('loan_amount')

        offer = self.session.query(Offer).filter_by(offer_id=offer_id, customer_id=customer_id).first()
        if not offer:
            raise ValueError("Offer not found for customer.")

        # Update offer status based on eligibility
        if eligibility_status == 'Eligible':
            offer.offer_status = 'Active' # Or 'Eligible' if a distinct status is needed
            offer.propensity = data.get('propensity', 'Very High') # Update propensity
            # If loan_amount needs to be stored with the offer, add a column or use JSONB
            # offer.event_details['loan_amount'] = loan_amount # Example if using JSONB
        else:
            offer.offer_status = 'Inactive' # Or 'Rejected'

        self.session.add(offer)
        self._commit_and_close()
        return True

    def process_realtime_status_update(self, data):
        """FR7, FR11, FR12: Receives real-time application status updates from Insta/E-aggregators or LOS."""
        loan_application_number = data.get('loan_application_number')
        customer_id = data.get('customer_id')
        current_stage = data.get('current_stage')
        status_timestamp = pd.to_datetime(data.get('status_timestamp'))

        # Store as an event (FR22, FR25, FR26)
        event = Event(
            customer_id=customer_id,
            event_type=f"LOS_{current_stage.upper()}",
            event_source=data.get('source', 'LOS'),
            event_timestamp=status_timestamp,
            event_details={"loan_application_number": loan_application_number, "stage": current_stage, "details": data.get('details')}
        )
        self.session.add(event)

        # Update customer's loan_application_number if it's a new journey or update
        customer = self.session.query(Customer).filter_by(customer_id=customer_id).first()
        if customer:
            # FR14: Prevent modification of customer offers with a started loan application journey
            # This check would be in OfferService methods, not here.
            # Here, we just update the LAN on the customer record.
            if not customer.loan_application_number or customer.loan_application_number != loan_application_number:
                customer.loan_application_number = loan_application_number
                self.session.add(customer)

        self._commit_and_close()
        return True

    def upload_customer_data_admin(self, file_content_base64, file_name, loan_type):
        """FR35, FR36, FR37, FR38: Uploads customer details file via Admin Portal."""
        import base64
        decoded_content = base64.b64decode(file_content_base64).decode('utf-8')
        df = pd.read_csv(io.StringIO(decoded_content))

        log_id = str(uuid.uuid4())
        success_count = 0
        error_records = []

        for index, row in df.iterrows():
            row_dict = row.to_dict()
            errors = self._validate_data_row(row_dict, loan_type)
            if errors:
                error_records.append({"row_data": row_dict, "errors": errors})
                continue

            try:
                customer_id, is_duplicate = self.customer_service.deduplicate_customer_data(row_dict)
                
                # FR36: Generate leads in the system upon successful file upload
                offer_data = {
                    "customer_id": customer_id,
                    "offer_type": "Fresh", # Assuming new offers from admin upload
                    "propensity": row_dict.get('propensity', 'Medium'),
                    "start_date": datetime.date.today(),
                    "end_date": datetime.date.today() + datetime.timedelta(days=90), # Example validity
                    "channel": f"Admin_Upload_{loan_type}"
                }
                self.session.add(Offer(**offer_data))
                success_count += 1
            except Exception as e:
                error_records.append({"row_data": row_dict, "errors": [str(e)]})

        status = 'SUCCESS' if not error_records else 'PARTIAL_SUCCESS' if success_count > 0 else 'FAILED'
        error_description = json.dumps(error_records) if error_records else None

        log_entry = IngestionLog(
            log_id=log_id,
            file_name=file_name,
            status=status,
            error_description=error_description
        )
        self.session.add(log_entry)
        self._commit_and_close()

        return {
            "log_id": log_id,
            "success_count": success_count,
            "error_count": len(error_records),
            "status": status
        }

class EventService(BaseService):
    """Service for capturing and storing customer event data."""

    def store_moengage_event(self, event_data):
        """FR22, FR24: Captures and stores SMS event data (sent, delivered, click) from Moengage."""
        customer_id = event_data.get('customer_id')
        event_type = event_data.get('event_type') # e.g., SMS_SENT, SMS_DELIVERED, SMS_CLICK
        event_timestamp = pd.to_datetime(event_data.get('event_timestamp'))
        details = event_data.get('details', {})

        event = Event(
            customer_id=customer_id,
            event_type=event_type,
            event_source="Moengage",
            event_timestamp=event_timestamp,
            event_details=details
        )
        self.session.add(event)
        self._commit_and_close()
        return event.event_id

    def store_los_event(self, event_data):
        """FR22, FR25, FR26: Captures and stores conversion/application stage data from LOS/Moengage."""
        customer_id = event_data.get('customer_id')
        event_type = event_data.get('event_type') # e.g., EKYC_ACHIEVED, DISBURSEMENT, LOAN_LOGIN, BUREAU_CHECK
        event_source = event_data.get('event_source', 'LOS') # Could be Moengage for conversion
        event_timestamp = pd.to_datetime(event_data.get('event_timestamp'))
        details = event_data.get('details', {})

        event = Event(
            customer_id=customer_id,
            event_type=event_type,
            event_source=event_source,
            event_timestamp=event_timestamp,
            event_details=details
        )
        self.session.add(event)
        self._commit_and_close()
        return event.event_id

class CampaignService(BaseService):
    """Service for generating campaign files and managing campaign metrics."""

    def generate_moengage_file(self):
        """FR31, FR44: Generates and allows download of the Moengage format CSV file for campaigns."""
        # Exclude DND customers (FR23)
        customers_for_campaign = self.session.query(Customer).filter(Customer.dnd_flag == False).all()
        
        # Get active offers for these customers
        customer_ids = [c.customer_id for c in customers_for_campaign]
        active_offers = self.session.query(Offer).filter(
            Offer.customer_id.in_(customer_ids),
            Offer.offer_status == 'Active',
            Offer.end_date >= datetime.date.today()
        ).all()

        # Join customer and offer data
        campaign_data = []
        customer_map = {c.customer_id: c for c in customers_for_campaign}

        for offer in active_offers:
            customer = customer_map.get(offer.customer_id)
            if customer:
                campaign_data.append({
                    "customer_id": customer.customer_id,
                    "mobile_number": customer.mobile_number,
                    "pan_number": customer.pan_number,
                    "aadhaar_number": customer.aadhaar_number,
                    "ucid_number": customer.ucid_number,
                    "offer_id": offer.offer_id,
                    "offer_type": offer.offer_type,
                    "propensity": offer.propensity,
                    "start_date": offer.start_date.isoformat() if offer.start_date else None,
                    "end_date": offer.end_date.isoformat() if offer.end_date else None,
                    "segment": customer.segment,
                    "channel": offer.channel,
                    # Add other fields required by Moengage format (Question 17)
                    # These are placeholders and would be defined by Moengage template.
                    "moengage_campaign_id": f"CMP_{offer.offer_id}",
                    "moengage_customer_attribute_1": "value_x",
                    "moengage_offer_details": f"{offer.offer_type}-{offer.propensity}"
                })

        df = pd.DataFrame(campaign_data)
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    def record_campaign_metrics(self, metrics_data):
        """FR30: Stores campaign metrics."""
        metric = CampaignMetric(
            campaign_unique_id=metrics_data['campaign_unique_id'],
            campaign_name=metrics_data.get('campaign_name'),
            campaign_date=pd.to_datetime(metrics_data.get('campaign_date')).date(),
            attempted_count=metrics_data.get('attempted_count'),
            sent_success_count=metrics_data.get('sent_success_count'),
            failed_count=metrics_data.get('failed_count'),
            conversion_rate=metrics_data.get('conversion_rate')
        )
        self.session.add(metric)
        self._commit_and_close()
        return metric.metric_id

class ReportService(BaseService):
    """Service for generating various reports and data downloads."""

    def get_daily_data_tally_report(self):
        """FR39: Provides data for daily reports for data tally."""
        total_customers = self.session.query(Customer).count()
        total_offers = self.session.query(Offer).count()
        active_offers = self.session.query(Offer).filter_by(offer_status='Active').count()
        expired_offers = self.session.query(Offer).filter_by(offer_status='Expired').count()
        events_today = self.session.query(Event).filter(
            Event.created_at >= datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        last_ingestion_log = self.session.query(IngestionLog).order_by(IngestionLog.upload_timestamp.desc()).first()
        last_log_timestamp = last_ingestion_log.upload_timestamp.isoformat() if last_ingestion_log else "N/A"

        report_data = {
            "report_date": datetime.date.today().isoformat(),
            "total_customers": total_customers,
            "total_offers": total_offers,
            "active_offers": active_offers,
            "expired_offers": expired_offers,
            "events_today": events_today,
            "last_data_ingestion": last_log_timestamp
        }
        return report_data

    def get_error_file(self, log_id):
        """FR34: Allows download of an Excel file detailing errors from data ingestion processes."""
        log_entry = self.session.query(IngestionLog).filter_by(log_id=log_id).first()
        if not log_entry or not log_entry.error_description:
            return None # Or raise an appropriate error

        try:
            error_data = json.loads(log_entry.error_description)
            df = pd.DataFrame(error_data)
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl') # Requires openpyxl to be installed
            output.seek(0)
            return output.getvalue()
        except json.JSONDecodeError:
            # Handle cases where error_description might not be valid JSON
            df = pd.DataFrame([{"log_id": log_id, "error": log_entry.error_description}])
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            return output.getvalue()

# --- Service Manager ---
# This class provides a centralized way to get instances of all services,
# managing their dependencies (like the database session).

class ServiceManager:
    """Manages the instantiation and provision of all application services."""
    def __init__(self):
        self._session_factory = Session # Use the SQLAlchemy sessionmaker

    def get_customer_service(self):
        """Returns an instance of CustomerService."""
        return CustomerService(self._session_factory())

    def get_offer_service(self):
        """Returns an instance of OfferService."""
        return OfferService(self._session_factory())

    def get_ingestion_service(self):
        """Returns an instance of IngestionService with its dependencies."""
        # IngestionService requires CustomerService and OfferService instances
        return IngestionService(
            self._session_factory(),
            self.get_customer_service(), # Pass a new instance for this request
            self.get_offer_service()     # Pass a new instance for this request
        )

    def get_event_service(self):
        """Returns an instance of EventService."""
        return EventService(self._session_factory())

    def get_campaign_service(self):
        """Returns an instance of CampaignService."""
        return CampaignService(self._session_factory())

    def get_report_service(self):
        """Returns an instance of ReportService."""
        return ReportService(self._session_factory())

# Instantiate the ServiceManager to make services accessible throughout the application.
# Other modules can import `service_manager` from `backend.src.services`.
service_manager = ServiceManager()

# Note on session management in a Flask application:
# In a real Flask app using Flask-SQLAlchemy, `db.session` is typically a scoped session
# managed per request. The `_commit_and_close` method in BaseService would be replaced
# by Flask-SQLAlchemy's `db.session.commit()` and `db.session.rollback()`,
# with `db.session.remove()` called automatically in a `teardown_request` handler.
# The current implementation creates a new session for each service instance, which is
# suitable for standalone testing or simple scripts, but less efficient for web requests.