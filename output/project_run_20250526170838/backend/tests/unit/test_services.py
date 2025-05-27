import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime, date, timedelta
import io
import pandas as pd
import xlsxwriter # Required by pandas for ExcelWriter engine


# Mock database session and models for unit testing
class MockCustomer:
    """Mock Customer model."""
    def __init__(self, customer_id=None, mobile_number=None, pan_number=None,
                 aadhaar_number=None, ucid_number=None,
                 loan_application_number=None, dnd_flag=False, segment=None,
                 created_at=None, updated_at=None):
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
        self.offers = []
        self.events = []

    def __repr__(self):
        return f"<MockCustomer {self.customer_id} - {self.mobile_number}>"

    def __eq__(self, other):
        if not isinstance(other, MockCustomer):
            return NotImplemented
        return self.customer_id == other.customer_id

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "mobile_number": self.mobile_number,
            "pan_number": self.pan_number,
            "aadhaar_number": self.aadhaar_number,
            "ucid_number": self.ucid_number,
            "loan_application_number": self.loan_application_number,
            "dnd_flag": self.dnd_flag,
            "segment": self.segment,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "offers": [o.to_dict() for o in self.offers],
            "journey_stages": [e.to_dict() for e in self.events]
        }


class MockOffer:
    """Mock Offer model."""
    def __init__(self, offer_id=None, customer_id=None, offer_type=None,
                 offer_status=None, propensity=None, start_date=None,
                 end_date=None, channel=None, created_at=None, updated_at=None):
        self.offer_id = offer_id or str(uuid.uuid4())
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.propensity = propensity
        self.start_date = start_date or date.today()
        self.end_date = end_date or (date.today() + timedelta(days=30))
        self.channel = channel
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self):
        return f"<MockOffer {self.offer_id} - {self.offer_status}>"

    def __eq__(self, other):
        if not isinstance(other, MockOffer):
            return NotImplemented
        return self.offer_id == other.offer_id


class MockEvent:
    """Mock Event model."""
    def __init__(self, event_id=None, customer_id=None, event_type=None,
                 event_source=None, event_timestamp=None, event_details=None,
                 created_at=None):
        self.event_id = event_id or str(uuid.uuid4())
        self.customer_id = customer_id
        self.event_type = event_type
        self.event_source = event_source
        self.event_timestamp = event_timestamp or datetime.now()
        self.event_details = event_details or {}
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"<MockEvent {self.event_id} - {self.event_type}>"

    def __eq__(self, other):
        if not isinstance(other, MockEvent):
            return NotImplemented
        return self.event_id == other.event_id


class MockIngestionLog:
    """Mock IngestionLog model."""
    def __init__(self, log_id=None, file_name=None, upload_timestamp=None,
                 status=None, error_description=None):
        self.log_id = log_id or str(uuid.uuid4())
        self.file_name = file_name
        self.upload_timestamp = upload_timestamp or datetime.now()
        self.status = status
        self.error_description = error_description

    def __repr__(self):
        return f"<MockIngestionLog {self.log_id} - {self.status}>"

    def __eq__(self, other):
        if not isinstance(other, MockIngestionLog):
            return NotImplemented
        # For testing, we might compare based on key attributes if ID is generated
        return (self.file_name == other.file_name and
                self.status == other.status and
                self.error_description == other.error_description)


class MockCampaignMetric:
    """Mock CampaignMetric model."""
    def __init__(self, metric_id=None, campaign_unique_id=None,
                 campaign_name=None, campaign_date=None, attempted_count=0,
                 sent_success_count=0, failed_count=0, conversion_rate=0.0,
                 created_at=None):
        self.metric_id = metric_id or str(uuid.uuid4())
        self.campaign_unique_id = campaign_unique_id or str(uuid.uuid4())
        self.campaign_name = campaign_name
        self.campaign_date = campaign_date or date.today()
        self.attempted_count = attempted_count
        self.sent_success_count = sent_success_count
        self.failed_count = failed_count
        self.conversion_rate = conversion_rate
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"<MockCampaignMetric {self.campaign_unique_id}>"

    def __eq__(self, other):
        if not isinstance(other, MockCampaignMetric):
            return NotImplemented
        return self.metric_id == other.metric_id


# Mock the db object and its session
class MockDB:
    """Mock database object to simulate SQLAlchemy db."""
    def __init__(self):
        self.session = MagicMock()
        self.Customer = MockCustomer
        self.Offer = MockOffer
        self.Event = MockEvent
        self.IngestionLog = MockIngestionLog
        self.CampaignMetric = MockCampaignMetric

db = MockDB()


# --- Mock Services (simplified for testing purposes) ---
# In a real application, these would be in separate files like
# backend/src/services/customer_service.py, etc.

class CustomerService:
    """Service for customer-related operations."""
    def __init__(self, db_session):
        self.db_session = db_session

    def create_or_update_customer(self, data):
        mobile = data.get("mobile_number")
        pan = data.get("pan_number")
        aadhaar = data.get("aadhaar_number")
        ucid = data.get("ucid_number")
        loan_app_num = data.get("loan_application_number")

        # Deduplication logic (simplified for service mock)
        existing_customer = None
        if mobile:
            existing_customer = self.db_session.query(db.Customer).filter_by(
                mobile_number=mobile).first()
        if not existing_customer and pan:
            existing_customer = self.db_session.query(db.Customer).filter_by(
                pan_number=pan).first()
        if not existing_customer and aadhaar:
            existing_customer = self.db_session.query(db.Customer).filter_by(
                aadhaar_number=aadhaar).first()
        if not existing_customer and ucid:
            existing_customer = self.db_session.query(db.Customer).filter_by(
                ucid_number=ucid).first()
        if not existing_customer and loan_app_num:
            existing_customer = self.db_session.query(db.Customer).filter_by(
                loan_application_number=loan_app_num).first()

        if existing_customer:
            # Update existing customer
            for key, value in data.items():
                if value is not None:
                    setattr(existing_customer, key, value)
            existing_customer.updated_at = datetime.now()
            self.db_session.add(existing_customer)
            return existing_customer, False  # False indicates update
        else:
            # Create new customer
            new_customer = db.Customer(**data)
            self.db_session.add(new_customer)
            return new_customer, True  # True indicates creation

    def get_customer_profile(self, customer_id):
        customer = self.db_session.query(db.Customer).filter_by(
            customer_id=customer_id).first()
        if customer:
            # In a real scenario, you'd eager load or query related offers/events
            # For mock, we'll assume they are attached or can be queried.
            customer.offers = self.db_session.query(db.Offer).filter_by(
                customer_id=customer_id).all()
            customer.events = self.db_session.query(db.Event).filter_by(
                customer_id=customer_id).all()
            return customer
        return None

    def update_dnd_status(self, customer_id, dnd_flag):
        customer = self.db_session.query(db.Customer).filter_by(
            customer_id=customer_id).first()
        if customer:
            customer.dnd_flag = dnd_flag
            customer.updated_at = datetime.now()
            self.db_session.add(customer)
            self.db_session.commit()
            return True
        return False


class OfferService:
    """Service for offer-related operations."""
    def __init__(self, db_session):
        self.db_session = db_session

    def create_offer(self, customer_id, offer_data):
        offer = db.Offer(customer_id=customer_id, **offer_data)
        self.db_session.add(offer)
        return offer

    def update_offer_status(self, offer_id, new_status):
        offer = self.db_session.query(db.Offer).filter_by(
            offer_id=offer_id).first()
        if offer:
            offer.offer_status = new_status
            offer.updated_at = datetime.now()
            self.db_session.add(offer)
            return True
        return False

    def apply_attribution_logic(self, customer_id):
        # Simplified attribution: pick the 'Fresh' offer if available,
        # else 'New-new', else any active.
        offers = self.db_session.query(db.Offer).filter_by(
            customer_id=customer_id, offer_status="Active"
        ).order_by(db.Offer.created_at.desc()).all()

        if not offers:
            return None

        fresh_offers = [o for o in offers if o.offer_type == "Fresh"]
        if fresh_offers:
            return fresh_offers[0]  # Pick the latest 'Fresh'

        new_new_offers = [o for o in offers if o.offer_type == "New-new"]
        if new_new_offers:
            return new_new_offers[0]  # Pick the latest 'New-new'

        return offers[0]  # Fallback to any latest active offer

    def mark_offers_expired(self):
        today = date.today()
        # FR41: Mark offers as expired based on offer end dates for
        # non-journey started customers.
        # This requires checking if a customer has an active journey.
        # For simplicity, we'll assume 'journey_started' is a flag or
        # determined by events.
        # Mocking this fully would require complex joins/subqueries.
        # For unit test, we'll mock the query result.
        offers_to_expire = self.db_session.query(db.Offer).filter(
            db.Offer.offer_status == "Active",
            db.Offer.end_date < today
        ).all()

        for offer in offers_to_expire:
            # In a real scenario, check if customer has started journey
            # For this mock, we'll just expire based on date.
            offer.offer_status = "Expired"
            offer.updated_at = datetime.now()
            self.db_session.add(offer)
        return len(offers_to_expire)


class IngestionService:
    """Service for data ingestion and validation."""
    def __init__(self, db_session, customer_service, offer_service):
        self.db_session = db_session
        self.customer_service = customer_service
        self.offer_service = offer_service

    def validate_customer_data(self, row):
        errors = []
        if not row.get("mobile_number") and not row.get("pan_number") and \
           not row.get("aadhaar_number") and not row.get("ucid_number") and \
           not row.get("loan_application_number"):
            errors.append("At least one identifier (mobile, PAN, Aadhaar, "
                          "UCID, LAN) is required.")
        if not row.get("offer_type"):
            errors.append("Offer type is required.")
        # Add more specific column-level validations as per FR1
        return errors

    def process_uploaded_customer_data(self, file_content, file_name,
                                        loan_type):
        log_id = str(uuid.uuid4())
        success_count = 0
        error_count = 0
        error_rows = []

        try:
            df = pd.read_csv(io.StringIO(file_content))
            df = df.where(pd.notnull(df), None)  # Replace NaN with None

            for index, row in df.iterrows():
                row_dict = row.to_dict()
                validation_errors = self.validate_customer_data(row_dict)

                if validation_errors:
                    error_count += 1
                    error_rows.append({"row_number": index + 2,
                                       "data": row_dict,
                                       "errors": validation_errors})
                    continue

                try:
                    customer_data = {
                        "mobile_number": (str(int(row_dict["mobile_number"]))
                                          if row_dict.get("mobile_number")
                                          is not None else None),
                        "pan_number": row_dict.get("pan_number"),
                        "aadhaar_number": row_dict.get("aadhaar_number"),
                        "ucid_number": row_dict.get("ucid_number"),
                        "loan_application_number": row_dict.get(
                            "loan_application_number"),
                        "segment": row_dict.get("segment"),
                        "dnd_flag": row_dict.get("dnd_flag", False)
                    }
                    customer, is_new = \
                        self.customer_service.create_or_update_customer(
                            customer_data)

                    offer_data = {
                        "offer_type": row_dict["offer_type"],
                        "offer_status": row_dict.get("offer_status", "Active"),
                        "propensity": row_dict.get("propensity"),
                        "start_date": (pd.to_datetime(row_dict["start_date"])
                                       .date() if row_dict.get("start_date")
                                       else date.today()),
                        "end_date": (pd.to_datetime(row_dict["end_date"])
                                     .date() if row_dict.get("end_date")
                                     else (date.today() + timedelta(days=30))),
                        "channel": row_dict.get("channel")
                    }
                    self.offer_service.create_offer(customer.customer_id,
                                                    offer_data)
                    success_count += 1
                    self.db_session.commit()
                except Exception as e:
                    self.db_session.rollback()
                    error_count += 1
                    error_rows.append({"row_number": index + 2,
                                       "data": row_dict, "errors": [str(e)]})

            status = ("SUCCESS" if error_count == 0 else
                      "PARTIAL_SUCCESS" if success_count > 0 else "FAILED")
            error_description = None
            if error_rows:
                # In real app, serialize error_rows to JSON or similar
                error_description = "Errors encountered during processing."

            log_entry = db.IngestionLog(
                log_id=log_id,
                file_name=file_name,
                status=status,
                error_description=error_description
            )
            self.db_session.add(log_entry)
            self.db_session.commit()

            return {
                "log_id": log_id,
                "success_count": success_count,
                "error_count": error_count,
                "error_rows": error_rows,
                "status": status
            }
        except Exception as e:
            self.db_session.rollback()
            log_entry = db.IngestionLog(
                log_id=log_id,
                file_name=file_name,
                status="FAILED",
                error_description=f"File processing failed: {str(e)}"
            )
            self.db_session.add(log_entry)
            self.db_session.commit()
            raise e


class EventService:
    """Service for recording customer events."""
    def __init__(self, db_session):
        self.db_session = db_session

    def record_event(self, customer_id, event_type, event_source,
                     event_details=None):
        event = db.Event(
            customer_id=customer_id,
            event_type=event_type,
            event_source=event_source,
            event_details=event_details
        )
        self.db_session.add(event)
        self.db_session.commit()
        return event


class CampaignService:
    """Service for campaign-related operations."""
    def __init__(self, db_session):
        self.db_session = db_session

    def generate_moengage_file(self):
        # FR44: Generate Moengage format file in .csv format,
        # uploadable in Moengage.
        # FR23: Avoid sending campaigns to DND customers.
        # This is a simplified representation. Actual Moengage file might
        # require specific columns.
        active_customers_with_offers = self.db_session.query(db.Customer).join(
            db.Offer).filter(
            db.Customer.dnd_flag is False,
            db.Offer.offer_status == "Active"
        ).distinct().all()

        if not active_customers_with_offers:
            return pd.DataFrame().to_csv(index=False)

        data = []
        for customer in active_customers_with_offers:
            # Get the attributed offer for this customer
            attributed_offer = self.db_session.query(db.Offer).filter_by(
                customer_id=customer.customer_id, offer_status="Active"
            ).order_by(db.Offer.created_at.desc()).first()  # Simplified

            if attributed_offer:
                data.append({
                    "customer_id": customer.customer_id,
                    "mobile_number": customer.mobile_number,
                    "pan_number": customer.pan_number,
                    "offer_id": attributed_offer.offer_id,
                    "offer_type": attributed_offer.offer_type,
                    "offer_status": attributed_offer.offer_status,
                    "propensity": attributed_offer.propensity,
                    "campaign_channel": attributed_offer.channel,
                    "offer_end_date": attributed_offer.end_date.isoformat()
                    # Add other Moengage specific fields as needed
                })
        if not data:
            return pd.DataFrame().to_csv(index=False)

        df = pd.DataFrame(data)
        return df.to_csv(index=False)


class ReportService:
    """Service for generating and downloading reports."""
    def __init__(self, db_session):
        self.db_session = db_session

    def get_duplicate_data(self):
        # FR32: Download a Duplicate Data File.
        # This is a conceptual mock. Actual deduplication logic would
        # identify duplicates.
        # For unit test, we'll return some mock data.
        # In a real scenario, this would query a 'duplicate_records' table
        # or run a deduplication report.
        mock_duplicates = [
            {"customer_id_1": "cust1", "mobile_number": "123",
             "customer_id_2": "cust1_dup", "reason": "mobile"},
            {"customer_id_1": "cust2", "pan_number": "ABC",
             "customer_id_2": "cust2_dup", "reason": "pan"}
        ]
        df = pd.DataFrame(mock_duplicates)
        return df.to_csv(index=False)

    def get_unique_data(self):
        # FR33: Download a Unique Data File.
        # This is a conceptual mock. Actual unique data would be derived
        # from the main customer table.
        mock_unique = [
            {"customer_id": "cust_u1", "mobile_number": "111", "segment": "C1"},
            {"customer_id": "cust_u2", "mobile_number": "222", "segment": "C2"}
        ]
        df = pd.DataFrame(mock_unique)
        return df.to_csv(index=False)

    def get_error_data(self):
        # FR34: Download an Error Excel file.
        # This would query the ingestion_logs table for failed/partial_success
        # entries.
        error_logs = self.db_session.query(db.IngestionLog).filter(
            db.IngestionLog.status.in_(["FAILED", "PARTIAL_SUCCESS"])
        ).all()

        data = []
        for log in error_logs:
            data.append({
                "log_id": log.log_id,
                "file_name": log.file_name,
                "upload_timestamp": log.upload_timestamp.isoformat(),
                "status": log.status,
                "error_description": log.error_description
            })
        df = pd.DataFrame(data)
        # For Excel, pandas can write to BytesIO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Errors')
        output.seek(0)
        return output.getvalue()


# Instantiate services with the mock db session
customer_service = CustomerService(db.session)
offer_service = OfferService(db.session)
ingestion_service = IngestionService(db.session, customer_service,
                                     offer_service)
event_service = EventService(db.session)
campaign_service = CampaignService(db.session)
report_service = ReportService(db.session)


# --- Unit Tests ---

@pytest.fixture(autouse=True)
def setup_mocks():
    """Resets the mock db session before each test."""
    db.session.reset_mock()
    db.session.query.return_value.filter_by.return_value.first.return_value = \
        None
    db.session.query.return_value.filter_by.return_value.all.return_value = []
    db.session.query.return_value.filter.return_value.all.return_value = []
    db.session.query.return_value.join.return_value.filter.return_value.\
        distinct.return_value.all.return_value = []
    db.session.query.return_value.filter.return_value.in_.return_value.\
        all.return_value = []
    db.session.query.return_value.filter_by.return_value.order_by.\
        return_value.first.return_value = None
    db.session.query.return_value.filter_by.return_value.order_by.\
        return_value.all.return_value = []

    # Mock uuid.uuid4 to return a predictable UUID for testing
    with patch('uuid.uuid4',
               return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')) \
            as mock_uuid:
        yield mock_uuid


class TestCustomerService:
    """Unit tests for CustomerService."""
    def test_create_new_customer_success(self):
        customer_data = {
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F",
            "segment": "C1"
        }
        db.session.query(db.Customer).filter_by.return_value.first.\
            return_value = None

        customer, is_new = customer_service.create_or_update_customer(
            customer_data)

        assert is_new is True
        assert customer.mobile_number == "9876543210"
        assert customer.pan_number == "ABCDE1234F"
        assert customer.segment == "C1"
        db.session.add.assert_called_once_with(customer)

    def test_update_existing_customer_by_mobile(self):
        existing_customer = MockCustomer(
            customer_id="existing_cust_id",
            mobile_number="9876543210",
            pan_number="OLD_PAN",
            segment="C0"
        )
        db.session.query(db.Customer).filter_by.return_value.first.\
            return_value = existing_customer

        customer_data = {
            "mobile_number": "9876543210",
            "pan_number": "NEW_PAN",
            "segment": "C1"
        }

        customer, is_new = customer_service.create_or_update_customer(
            customer_data)

        assert is_new is False
        assert customer.customer_id == "existing_cust_id"
        assert customer.pan_number == "NEW_PAN"
        assert customer.segment == "C1"
        db.session.add.assert_called_once_with(customer)

    def test_get_customer_profile_found(self):
        customer_id = "test_cust_id"
        mock_customer = MockCustomer(customer_id=customer_id,
                                     mobile_number="111222333")
        mock_offer = MockOffer(customer_id=customer_id, offer_status="Active")
        mock_event = MockEvent(customer_id=customer_id, event_type="SMS_SENT")

        db.session.query(db.Customer).filter_by.return_value.first.\
            return_value = mock_customer
        db.session.query(db.Offer).filter_by.return_value.all.return_value = \
            [mock_offer]
        db.session.query(db.Event).filter_by.return_value.all.return_value = \
            [mock_event]

        customer = customer_service.get_customer_profile(customer_id)

        assert customer is not None
        assert customer.customer_id == customer_id
        assert len(customer.offers) == 1
        assert len(customer.events) == 1
        db.session.query(db.Customer).filter_by.assert_called_with(
            customer_id=customer_id)
        db.session.query(db.Offer).filter_by.assert_called_with(
            customer_id=customer_id)
        db.session.query(db.Event).filter_by.assert_called_with(
            customer_id=customer_id)

    def test_get_customer_profile_not_found(self):
        db.session.query(db.Customer).filter_by.return_value.first.\
            return_value = None
        customer = customer_service.get_customer_profile("non_existent_id")
        assert customer is None

    def test_update_dnd_status_success(self):
        customer_id = "test_cust_id"
        mock_customer = MockCustomer(customer_id=customer_id, dnd_flag=False)
        db.session.query(db.Customer).filter_by.return_value.first.\
            return_value = mock_customer

        result = customer_service.update_dnd_status(customer_id, True)

        assert result is True
        assert mock_customer.dnd_flag is True
        db.session.add.assert_called_once_with(mock_customer)
        db.session.commit.assert_called_once()

    def test_update_dnd_status_not_found(self):
        db.session.query(db.Customer).filter_by.return_value.first.\
            return_value = None
        result = customer_service.update_dnd_status("non_existent_id", True)
        assert result is False
        db.session.add.assert_not_called()
        db.session.commit.assert_not_called()


class TestOfferService:
    """Unit tests for OfferService."""
    def test_create_offer_success(self):
        customer_id = "test_cust_id"
        offer_data = {
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity": "High",
            "channel": "API"
        }
        offer = offer_service.create_offer(customer_id, offer_data)

        assert offer.customer_id == customer_id
        assert offer.offer_type == "Fresh"
        assert offer.offer_status == "Active"
        db.session.add.assert_called_once_with(offer)

    def test_update_offer_status_success(self):
        offer_id = "test_offer_id"
        mock_offer = MockOffer(offer_id=offer_id, offer_status="Active")
        db.session.query(db.Offer).filter_by.return_value.first.\
            return_value = mock_offer

        result = offer_service.update_offer_status(offer_id, "Expired")

        assert result is True
        assert mock_offer.offer_status == "Expired"
        db.session.add.assert_called_once_with(mock_offer)

    def test_update_offer_status_not_found(self):
        db.session.query(db.Offer).filter_by.return_value.first.\
            return_value = None
        result = offer_service.update_offer_status("non_existent_id",
                                                    "Expired")
        assert result is False
        db.session.add.assert_not_called()

    def test_apply_attribution_logic_fresh_offer(self):
        customer_id = "cust_id_attr"
        offer1 = MockOffer(customer_id=customer_id, offer_type="New-new",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 1))
        offer2 = MockOffer(customer_id=customer_id, offer_type="Fresh",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 2))
        offer3 = MockOffer(customer_id=customer_id, offer_type="Enrich",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 3))

        db.session.query(db.Offer).filter_by.return_value.order_by.\
            return_value.all.return_value = [offer3, offer2, offer1]

        attributed_offer = offer_service.apply_attribution_logic(customer_id)
        assert attributed_offer == offer2  # Should pick Fresh

    def test_apply_attribution_logic_new_new_offer(self):
        customer_id = "cust_id_attr"
        offer1 = MockOffer(customer_id=customer_id, offer_type="Enrich",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 1))
        offer2 = MockOffer(customer_id=customer_id, offer_type="New-new",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 2))
        offer3 = MockOffer(customer_id=customer_id, offer_type="Enrich",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 3))

        db.session.query(db.Offer).filter_by.return_value.order_by.\
            return_value.all.return_value = [offer3, offer2, offer1]

        attributed_offer = offer_service.apply_attribution_logic(customer_id)
        assert attributed_offer == offer2  # Should pick New-new

    def test_apply_attribution_logic_fallback_latest(self):
        customer_id = "cust_id_attr"
        offer1 = MockOffer(customer_id=customer_id, offer_type="Enrich",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 1))
        offer2 = MockOffer(customer_id=customer_id, offer_type="Enrich",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 2))
        offer3 = MockOffer(customer_id=customer_id, offer_type="Old",
                           offer_status="Active",
                           created_at=datetime(2023, 1, 3))

        db.session.query(db.Offer).filter_by.return_value.order_by.\
            return_value.all.return_value = [offer3, offer2, offer1]

        attributed_offer = offer_service.apply_attribution_logic(customer_id)
        assert attributed_offer == offer3  # Should pick the latest active offer

    def test_apply_attribution_logic_no_active_offers(self):
        customer_id = "cust_id_attr"
        db.session.query(db.Offer).filter_by.return_value.order_by.\
            return_value.all.return_value = []
        attributed_offer = offer_service.apply_attribution_logic(customer_id)
        assert attributed_offer is None

    @patch('datetime.date')
    def test_mark_offers_expired(self, mock_date):
        mock_date.today.return_value = date(2023, 1, 15)
        offer1 = MockOffer(offer_id="o1", offer_status="Active",
                           end_date=date(2023, 1, 10))
        offer2 = MockOffer(offer_id="o2", offer_status="Active",
                           end_date=date(2023, 1, 20))
        offer3 = MockOffer(offer_id="o3", offer_status="Expired",
                           end_date=date(2023, 1, 1))

        db.session.query(db.Offer).filter.return_value.all.return_value = \
            [offer1, offer2, offer3]

        expired_count = offer_service.mark_offers_expired()

        assert expired_count == 1
        assert offer1.offer_status == "Expired"
        assert offer2.offer_status == "Active"  # Not expired yet
        assert offer3.offer_status == "Expired"  # Already expired
        db.session.add.assert_called_once_with(offer1)  # Only offer1 updated


class TestIngestionService:
    """Unit tests for IngestionService."""
    @patch.object(CustomerService, 'create_or_update_customer')
    @patch.object(OfferService, 'create_offer')
    @patch('pandas.read_csv')
    def test_process_uploaded_customer_data_success(self, mock_read_csv,
                                                    mock_create_offer,
                                                    mock_create_or_update_customer):
        mock_read_csv.return_value = pd.DataFrame({
            "mobile_number": ["9998887770"],
            "pan_number": ["ABCDE1234G"],
            "offer_type": ["Fresh"],
            "offer_status": ["Active"],
            "propensity": ["Medium"],
            "start_date": ["2023-01-01"],
            "end_date": ["2023-01-31"],
            "channel": ["Web"],
            "segment": ["C1"],
            "dnd_flag": [False]
        })
        mock_customer = MockCustomer(customer_id="new_cust_id")
        mock_create_or_update_customer.return_value = (mock_customer, True)
        mock_create_offer.return_value = MockOffer(customer_id="new_cust_id")

        file_content = "mobile_number,pan_number,offer_type,...\n" \
                       "9998887770,ABCDE1234G,Fresh,..."
        file_name = "test_upload.csv"
        loan_type = "Prospect"

        result = ingestion_service.process_uploaded_customer_data(
            file_content, file_name, loan_type)

        assert result["success_count"] == 1
        assert result["error_count"] == 0
        assert result["status"] == "SUCCESS"
        mock_read_csv.assert_called_once()
        mock_create_or_update_customer.assert_called_once()
        mock_create_offer.assert_called_once()
        db.session.commit.assert_called_once()
        # Assert on the attributes of the added IngestionLog
        added_log = db.session.add.call_args[0][0]
        assert isinstance(added_log, db.IngestionLog)
        assert added_log.file_name == file_name
        assert added_log.status == "SUCCESS"
        assert added_log.error_description is None

    @patch.object(CustomerService, 'create_or_update_customer')
    @patch.object(OfferService, 'create_offer')
    @patch('pandas.read_csv')
    def test_process_uploaded_customer_data_with_errors(self, mock_read_csv,
                                                        mock_create_offer,
                                                        mock_create_or_update_customer):
        mock_read_csv.return_value = pd.DataFrame({
            "mobile_number": ["9998887770", None],  # Second row has missing
            "pan_number": ["ABCDE1234G", None],
            "offer_type": ["Fresh", None],  # Second row has missing
            "offer_status": ["Active", "Active"],
            "propensity": ["Medium", "Low"],
            "start_date": ["2023-01-01", "2023-01-01"],
            "end_date": ["2023-01-31", "2023-01-31"],
            "channel": ["Web", "App"],
            "segment": ["C1", "C2"],
            "dnd_flag": [False, False]
        })
        mock_customer = MockCustomer(customer_id="new_cust_id")
        mock_create_or_update_customer.return_value = (mock_customer, True)
        mock_create_offer.return_value = MockOffer(customer_id="new_cust_id")

        file_content = "mobile_number,pan_number,offer_type,...\n" \
                       "9998887770,ABCDE1234G,Fresh,...\n,,,"
        file_name = "test_upload_errors.csv"
        loan_type = "Prospect"

        result = ingestion_service.process_uploaded_customer_data(
            file_content, file_name, loan_type)

        assert result["success_count"] == 1
        assert result["error_count"] == 1
        assert result["status"] == "PARTIAL_SUCCESS"
        assert len(result["error_rows"]) == 1
        assert result["error_rows"][0]["row_number"] == 2
        assert "At least one identifier" in result["error_rows"][0]["errors"]
        assert "Offer type is required" in result["error_rows"][0]["errors"]
        mock_read_csv.assert_called_once()
        # Only called for the first successful row
        mock_create_or_update_customer.assert_called_once()
        # Only called for the first successful row
        mock_create_offer.assert_called_once()
        assert db.session.commit.call_count == 2  # One for successful row, one for log
        assert db.session.rollback.call_count == 0  # No rollback for individual
        # Assert on the attributes of the added IngestionLog
        added_log = db.session.add.call_args[0][0]
        assert isinstance(added_log, db.IngestionLog)
        assert added_log.file_name == file_name
        assert added_log.status == "PARTIAL_SUCCESS"
        assert added_log.error_description == "Errors encountered during processing."

    def test_validate_customer_data_valid(self):
        row = {
            "mobile_number": "1234567890",
            "offer_type": "Fresh"
        }
        errors = ingestion_service.validate_customer_data(row)
        assert not errors

    def test_validate_customer_data_missing_identifiers(self):
        row = {
            "offer_type": "Fresh"
        }
        errors = ingestion_service.validate_customer_data(row)
        assert "At least one identifier" in errors[0]

    def test_validate_customer_data_missing_offer_type(self):
        row = {
            "mobile_number": "1234567890"
        }
        errors = ingestion_service.validate_customer_data(row)
        assert "Offer type is required" in errors[0]


class TestEventService:
    """Unit tests for EventService."""
    def test_record_event_success(self):
        customer_id = "event_cust_id"
        event_data = {
            "event_type": "EKYC_ACHIEVED",
            "event_source": "LOS",
            "event_details": {"status": "completed"}
        }
        event = event_service.record_event(customer_id, **event_data)

        assert event.customer_id == customer_id
        assert event.event_type == "EKYC_ACHIEVED"
        assert event.event_source == "LOS"
        assert event.event_details == {"status": "completed"}
        db.session.add.assert_called_once_with(event)
        db.session.commit.assert_called_once()


class TestCampaignService:
    """Unit tests for CampaignService."""
    def test_generate_moengage_file_success(self):
        customer1 = MockCustomer(customer_id="c1", mobile_number="111",
                                 dnd_flag=False)
        customer2 = MockCustomer(customer_id="c2", mobile_number="222",
                                 dnd_flag=True)  # DND customer
        customer3 = MockCustomer(customer_id="c3", mobile_number="333",
                                 dnd_flag=False)

        offer1 = MockOffer(customer_id="c1", offer_id="o1",
                           offer_type="Fresh", offer_status="Active",
                           channel="Web")
        offer2 = MockOffer(customer_id="c2", offer_id="o2",
                           offer_type="New-new", offer_status="Active",
                           channel="App")
        offer3 = MockOffer(customer_id="c3", offer_id="o3",
                           offer_type="Enrich", offer_status="Active",
                           channel="SMS")
        MockOffer(customer_id="c1", offer_id="o4",
                  offer_type="Expired", offer_status="Expired", channel="Web")

        # Mock the query for active customers with offers (excluding DND)
        db.session.query(db.Customer).join(db.Offer).filter.return_value.\
            distinct.return_value.all.return_value = [customer1, customer3]

        # Mock the query for attributed offer for each customer
        def mock_filter_by_order_by_first(customer_id, offer_status):
            if customer_id == "c1":
                return offer1
            if customer_id == "c3":
                return offer3
            return None

        db.session.query(db.Offer).filter_by.return_value.order_by.\
            return_value.first.side_effect = mock_filter_by_order_by_first

        csv_content = campaign_service.generate_moengage_file()
        df = pd.read_csv(io.StringIO(csv_content))

        assert len(df) == 2  # Only customer1 and customer3 should be included
        assert "customer_id" in df.columns
        assert "mobile_number" in df.columns
        assert "offer_id" in df.columns
        assert "offer_type" in df.columns
        assert "campaign_channel" in df.columns

        assert df["customer_id"].tolist() == ["c1", "c3"]
        assert df["mobile_number"].tolist() == ["111", "333"]
        assert df["offer_type"].tolist() == ["Fresh", "Enrich"]

    def test_generate_moengage_file_no_active_offers(self):
        db.session.query(db.Customer).join(db.Offer).filter.return_value.\
            distinct.return_value.all.return_value = []
        csv_content = campaign_service.generate_moengage_file()
        df = pd.read_csv(io.StringIO(csv_content))
        assert len(df) == 0
        assert df.empty is True


class TestReportService:
    """Unit tests for ReportService."""
    def test_get_duplicate_data(self):
        csv_content = report_service.get_duplicate_data()
        df = pd.read_csv(io.StringIO(csv_content))
        assert len(df) == 2
        assert "customer_id_1" in df.columns
        assert df["mobile_number"].iloc[0] == "123"

    def test_get_unique_data(self):
        csv_content = report_service.get_unique_data()
        df = pd.read_csv(io.StringIO(csv_content))
        assert len(df) == 2
        assert "customer_id" in df.columns
        assert df["mobile_number"].iloc[0] == "111"

    def test_get_error_data(self):
        log1 = MockIngestionLog(log_id="log1", file_name="file1.csv",
                                status="FAILED", error_description="Error 1")
        log2 = MockIngestionLog(log_id="log2", file_name="file2.csv",
                                status="PARTIAL_SUCCESS",
                                error_description="Error 2")
        MockIngestionLog(log_id="log3", file_name="file3.csv",
                         status="SUCCESS", error_description=None)

        db.session.query(db.IngestionLog).filter.return_value.in_.\
            return_value.all.return_value = [log1, log2]

        excel_content = report_service.get_error_data()
        # Read Excel content using pandas
        df = pd.read_excel(io.BytesIO(excel_content))

        assert len(df) == 2
        assert "log_id" in df.columns
        assert df["file_name"].tolist() == ["file1.csv", "file2.csv"]
        assert df["status"].tolist() == ["FAILED", "PARTIAL_SUCCESS"]
        assert df["error_description"].tolist() == ["Error 1", "Error 2"]