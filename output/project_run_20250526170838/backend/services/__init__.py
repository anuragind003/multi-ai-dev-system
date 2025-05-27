import uuid
import pandas as pd
import io
import base64
from datetime import datetime

# In a real Flask application, `db` would be imported from `backend.extensions`
# and models from `backend.models`.
# For the purpose of this single file, we will simulate database interactions
# and define minimal placeholder classes for data structures.


# Placeholder for a database session object.
# In a real Flask app, this would be `db.session` from Flask-SQLAlchemy.
class MockDBSession:
    """A mock database session for demonstration purposes."""
    def add(self, instance):
        # In a real scenario, this would add an instance to the session.
        pass

    def commit(self):
        # In a real scenario, this would commit the transaction.
        pass

    def rollback(self):
        # In a real scenario, this would roll back the transaction.
        pass

    def query(self, model):
        # Simulate a query object for basic filtering.
        return MockQuery(model)


class MockQuery:
    """A mock query object for simulating database queries."""
    def __init__(self, model):
        self.model = model
        self.filters = {}

    def filter_by(self, **kwargs):
        self.filters.update(kwargs)
        return self

    def first(self):
        # Simulate fetching the first record based on filters.
        if self.model.__name__ == "Customer" and \
           self.filters.get("customer_id") == "test-customer-123":
            return Customer(
                customer_id="test-customer-123",
                mobile_number="9876543210",
                pan_number="ABCDE1234F",
                aadhaar_number="123456789012",
                ucid_number="UCID001",
                loan_application_number="LAN001",
                dnd_flag=False,
                segment="C1"
            )
        if self.model.__name__ == "IngestionLog" and \
           self.filters.get("log_id") == "mock-log-id":
            # Simulate an existing log to prevent duplicate adds in finally block
            return IngestionLog("mock-log-id", "mock_file.csv",
                                datetime.utcnow(), "SUCCESS", None)
        return None

    def all(self):
        # Simulate fetching all records.
        if self.model.__name__ == "Customer":
            return [
                Customer("cust1", "9999999999", "XYZAB1234C", None, None, None, False, "C1"),
                Customer("cust2", "8888888888", "PQRST5678D", None, None, None, False, "C2"),
            ]
        return []


# Placeholder for Flask's current_app.logger
class MockLogger:
    """A mock logger for capturing log messages."""
    def info(self, message):
        # print(f"INFO: {message}")
        pass

    def error(self, message):
        # print(f"ERROR: {message}")
        pass


# Placeholder for Flask's current_app
class MockCurrentApp:
    """A mock Flask current_app object."""
    def __init__(self):
        self.logger = MockLogger()


# Assume current_app is available in a Flask context.
# For standalone execution, we'll use the mock.
try:
    from flask import current_app
except ImportError:
    current_app = MockCurrentApp()


# --- Placeholder Models (in a real app, these would be in backend/models.py) ---
class Customer:
    """Simplified Customer model based on database schema."""
    def __init__(self, customer_id, mobile_number, pan_number, aadhaar_number,
                 ucid_number, loan_application_number, dnd_flag, segment):
        self.customer_id = customer_id
        self.mobile_number = mobile_number
        self.pan_number = pan_number
        self.aadhaar_number = aadhaar_number
        self.ucid_number = ucid_number
        self.loan_application_number = loan_application_number
        self.dnd_flag = dnd_flag
        self.segment = segment
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        """Converts customer object to a dictionary."""
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
        }


class Offer:
    """Simplified Offer model based on database schema."""
    def __init__(self, offer_id, customer_id, offer_type, offer_status,
                 propensity, start_date, end_date, channel):
        self.offer_id = offer_id
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.propensity = propensity
        self.start_date = start_date
        self.end_date = end_date
        self.channel = channel
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class Event:
    """Simplified Event model based on database schema."""
    def __init__(self, event_id, customer_id, event_type, event_source,
                 event_timestamp, event_details):
        self.event_id = event_id
        self.customer_id = customer_id
        self.event_type = event_type
        self.event_source = event_source
        self.event_timestamp = event_timestamp
        self.event_details = event_details
        self.created_at = datetime.utcnow()


class IngestionLog:
    """Simplified IngestionLog model based on database schema."""
    def __init__(self, log_id, file_name, upload_timestamp, status, error_description):
        self.log_id = log_id
        self.file_name = file_name
        self.upload_timestamp = upload_timestamp
        self.status = status
        self.error_description = error_description


# --- Base Service Class ---
class BaseService:
    """
    A base class for services to provide access to the database session.
    """
    def __init__(self, db_session=None):
        # If db_session is not provided, use a mock for standalone testing.
        # In a real Flask app, this would typically be `db.session` from Flask-SQLAlchemy.
        self._db_session = db_session if db_session is not None else MockDBSession()

    @property
    def db_session(self):
        """Provides access to the database session."""
        return self._db_session


# --- Service Implementations ---

class CustomerService(BaseService):
    """
    Handles customer-related operations, including deduplication and profile management.
    Corresponds to FR2, FR3, FR4, FR5, FR6, FR15, FR20.
    """
    def get_customer_profile(self, customer_id):
        """
        Retrieves a single customer's profile view. (FR2, FR40)
        """
        customer = self.db_session.query(Customer).filter_by(
            customer_id=customer_id).first()
        if customer:
            # Simulate fetching offers and journey stages.
            # In a real app, this would involve more complex queries/joins.
            mock_offers = [
                {
                    "offer_id": str(uuid.uuid4()),
                    "offer_type": "Fresh",
                    "offer_status": "Active",
                    "propensity": "High",
                    "start_date": "2023-01-01",
                    "end_date": "2023-03-31"
                }
            ]
            mock_journey_stages = [
                {
                    "event_type": "LOAN_LOGIN",
                    "event_timestamp": "2023-01-15T10:00:00Z",
                    "source": "LOS"
                }
            ]
            profile = customer.to_dict()
            profile["current_offers"] = mock_offers
            profile["journey_stages"] = mock_journey_stages
            return profile
        return None

    def deduplicate_customer_data(self, customer_data_list):
        """
        Performs deduplication logic on customer data. (FR3, FR4, FR5, FR6)
        Returns unique and duplicate records from the provided batch.
        """
        unique_records = []
        duplicate_records = []
        processed_identifiers = set()  # To track identifiers within the current batch

        for record in customer_data_list:
            is_duplicate_in_batch = False
            identifiers = [
                record.get('mobile_number'),
                record.get('pan_number'),
                record.get('aadhaar_number'),
                record.get('ucid_number'),
                record.get('loan_application_number')
            ]

            # Check for duplicates within the current batch.
            for identifier in identifiers:
                if identifier and identifier in processed_identifiers:
                    is_duplicate_in_batch = True
                    break

            if is_duplicate_in_batch:
                duplicate_records.append(record)
                continue

            # Simulate checking against existing database (CDP and Customer 360 'live book').
            # This is a simplified check. A real implementation would involve DB queries.
            # For example:
            # existing_customer = self.db_session.query(Customer).filter(
            #     (Customer.mobile_number == record.get('mobile_number')) |
            #     (Customer.pan_number == record.get('pan_number')) |
            #     ...
            # ).first()
            # if existing_customer:
            #     duplicate_records.append(record)
            #     continue

            # If not a duplicate, add identifiers to processed set and to unique list.
            for identifier in identifiers:
                if identifier:
                    processed_identifiers.add(identifier)
            unique_records.append(record)

        return unique_records, duplicate_records


class IngestionService(BaseService):
    """
    Handles data ingestion from various sources. (FR1, FR7, FR9, FR11, FR12, FR35, FR36, FR37, FR38)
    """
    def process_realtime_lead(self, lead_data):
        """
        Processes real-time lead generation data. (FR11, FR12)
        Performs basic validation and inserts/updates customer data.
        """
        # FR1: Basic column-level validation.
        required_fields = ['mobile_number', 'loan_type', 'source_channel']
        if not all(lead_data.get(field) for field in required_fields):
            current_app.logger.error("Missing required lead data fields.")
            return {"status": "error", "message": "Missing required lead data fields."}, None

        try:
            # Simulate deduplication and insertion.
            # In a real scenario, this would involve CustomerService.deduplicate_customer_data
            # and then saving the unique customer.
            customer_id = str(uuid.uuid4())
            new_customer = Customer(
                customer_id=customer_id,
                mobile_number=lead_data.get('mobile_number'),
                pan_number=lead_data.get('pan_number'),
                aadhaar_number=lead_data.get('aadhaar_number'),
                ucid_number=lead_data.get('ucid_number'),
                loan_application_number=lead_data.get('loan_application_number'),
                dnd_flag=False,  # Default
                segment=None  # Default
            )
            self.db_session.add(new_customer)
            self.db_session.commit()
            current_app.logger.info(f"Processed new lead for customer_id: {customer_id}")
            return {"status": "success", "message": "Lead processed successfully."}, customer_id
        except Exception as e:
            current_app.logger.error(f"Database error processing lead: {e}")
            self.db_session.rollback()
            return {"status": "error", "message": "Database error or unexpected error."}, None

    def upload_customer_data_file(self, file_content_base64, file_name, loan_type):
        """
        Handles CSV file upload for customer details. (FR35, FR36, FR37, FR38)
        file_content_base64: base64 encoded string of the CSV file.
        """
        log_id = str(uuid.uuid4())
        success_count = 0
        error_count = 0
        errors = []
        status = "FAILED"

        try:
            # Decode base64 content.
            decoded_content = base64.b64decode(file_content_base64).decode('utf-8')
            df = pd.read_csv(io.StringIO(decoded_content))

            # FR1: Basic column-level validation.
            # These are example columns. Actual columns would come from
            # 'Dataset_Validations_UnifiedCL_v1.1 (1).xlsx'.
            expected_columns = ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number']
            if not all(col in df.columns for col in expected_columns):
                errors.append({"row": "N/A", "error_desc": "Missing essential columns in CSV."})
                current_app.logger.error(f"File {file_name} upload failed: Missing essential columns.")
                self.db_session.add(IngestionLog(log_id, file_name, datetime.utcnow(),
                                                  "FAILED", "Missing essential columns"))
                self.db_session.commit()
                return {
                    "status": "failed",
                    "log_id": log_id,
                    "success_count": 0,
                    "error_count": len(errors),
                    "errors": errors
                }

            customer_data_list = df.to_dict(orient='records')

            # FR3, FR4, FR5, FR6: Deduplication.
            customer_service = CustomerService(self.db_session)
            unique_records, duplicate_records = customer_service.deduplicate_customer_data(
                customer_data_list)

            for record in unique_records:
                try:
                    # Simulate lead generation (FR36) and saving to DB.
                    new_customer = Customer(
                        customer_id=str(uuid.uuid4()),
                        mobile_number=record.get('mobile_number'),
                        pan_number=record.get('pan_number'),
                        aadhaar_number=record.get('aadhaar_number'),
                        ucid_number=record.get('ucid_number'),
                        loan_application_number=record.get('loan_application_number'),
                        dnd_flag=record.get('dnd_flag', False),
                        segment=record.get('segment')
                    )
                    self.db_session.add(new_customer)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append({"row_data": record, "error_desc": str(e)})
                    current_app.logger.error(f"Error processing record in {file_name}: {e}")

            self.db_session.commit()  # Commit all unique records.

            # Simulate saving duplicates to a separate log/table if needed (FR32).
            # For now, they are just identified.

            status = "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS"
            error_desc = None if error_count == 0 else "Errors encountered during processing."
            self.db_session.add(IngestionLog(log_id, file_name, datetime.utcnow(), status, error_desc))
            self.db_session.commit()

            return {
                "status": status,
                "log_id": log_id,
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors
            }

        except base64.binascii.Error:
            errors.append({"row": "N/A", "error_desc": "Invalid base64 encoding."})
            status = "FAILED"
        except pd.errors.EmptyDataError:
            errors.append({"row": "N/A", "error_desc": "Uploaded file is empty."})
            status = "FAILED"
        except pd.errors.ParserError:
            errors.append({"row": "N/A", "error_desc": "Could not parse CSV file. Check format."})
            status = "FAILED"
        except Exception as e:
            current_app.logger.error(f"Error during file upload processing for {file_name}: {e}")
            errors.append({"row": "N/A", "error_desc": f"Internal server error: {str(e)}"})
            status = "FAILED"
        finally:
            # Ensure log is committed even on general failure.
            try:
                # Only add log if not already added in case of early exit.
                # This logic might need refinement in a real app to avoid duplicate logs.
                # For now, assume it's the final logging attempt.
                if not self.db_session.query(IngestionLog).filter_by(log_id=log_id).first():
                    self.db_session.add(IngestionLog(log_id, file_name, datetime.utcnow(),
                                                      status, errors[0]['error_desc'] if errors else None))
                    self.db_session.commit()
            except Exception as e:
                current_app.logger.error(f"Failed to log ingestion status: {e}")
                self.db_session.rollback()

        return {
            "status": status,
            "log_id": log_id,
            "success_count": success_count,
            "error_count": len(errors),
            "errors": errors
        }


class OfferService(BaseService):
    """
    Handles offer management and lifecycle. (FR8, FR14, FR16, FR17, FR18, FR19, FR41, FR42, FR43, FR44)
    """
    def update_offer_status(self, offer_id, new_status):
        """
        Updates the status of an offer. (FR16)
        """
        # Simulate fetching and updating offer.
        # offer = self.db_session.query(Offer).filter_by(offer_id=offer_id).first()
        # if offer:
        #     offer.offer_status = new_status
        #     self.db_session.commit()
        #     return {"status": "success", "message": f"Offer {offer_id} status updated to {new_status}"}
        current_app.logger.info(f"Simulating update of offer {offer_id} to {new_status}")
        return {"status": "success", "message": f"Offer {offer_id} status updated to {new_status}"}

    def generate_moengage_file(self):
        """
        Generates the Moengage format CSV file. (FR31, FR44)
        This is a simplified representation.
        """
        # Simulate fetching data for Moengage export, ensuring DND customers are excluded (FR23).
        # In a real scenario, this would involve complex queries and filtering.
        # For now, return dummy CSV content.
        csv_content = (
            "customer_id,mobile_number,offer_id,offer_type,campaign_segment,propensity\n"
            "cust1,9999999999,offerA,Fresh,C1,High\n"
            "cust2,8888888888,offerB,Enrich,C2,Medium\n"
        )
        current_app.logger.info("Generated mock Moengage file content.")
        return csv_content


class EventService(BaseService):
    """
    Handles event tracking and storage. (FR22, FR24, FR25, FR26)
    """
    def record_event(self, customer_id, event_type, event_source, event_details):
        """
        Records a customer event.
        """
        new_event = Event(
            event_id=str(uuid.uuid4()),
            customer_id=customer_id,
            event_type=event_type,
            event_source=event_source,
            event_timestamp=datetime.utcnow(),
            event_details=event_details
        )
        self.db_session.add(new_event)
        self.db_session.commit()
        current_app.logger.info(f"Recorded event {event_type} for customer {customer_id}")
        return {"status": "success", "message": "Event recorded."}


class ReportService(BaseService):
    """
    Handles generation of various reports and data downloads. (FR32, FR33, FR34, FR39, FR40)
    """
    def get_duplicate_data_file(self):
        """
        Generates a file containing identified duplicate customer records. (FR32)
        """
        # Simulate fetching duplicate data from a log or dedicated table.
        df_duplicates = pd.DataFrame({
            'mobile_number': ['9876543210', '1122334455'],
            'pan_number': ['ABCDE1234F', 'FGHIJ5678K'],
            'duplicate_reason': ['Mobile and PAN match', 'Aadhaar match'],
            'original_customer_id': ['cust_orig_1', 'cust_orig_2']
        })
        csv_content = df_duplicates.to_csv(index=False)
        current_app.logger.info("Generated mock duplicate data file content.")
        return csv_content

    def get_unique_data_file(self):
        """
        Generates a file containing unique customer records after deduplication. (FR33)
        """
        # Simulate fetching unique data.
        df_unique = pd.DataFrame({
            'customer_id': ['cust1', 'cust2', 'cust3'],
            'mobile_number': ['9999999999', '8888888888', '7777777777'],
            'pan_number': ['XYZAB1234C', 'PQRST5678D', 'LMNOP9012E'],
            'segment': ['C1', 'C2', 'C3']
        })
        csv_content = df_unique.to_csv(index=False)
        current_app.logger.info("Generated mock unique data file content.")
        return csv_content

    def get_error_data_file(self):
        """
        Generates an Excel file detailing errors from data ingestion processes. (FR34)
        """
        # Simulate fetching error data from ingestion_logs.
        df_errors = pd.DataFrame({
            'timestamp': [datetime.utcnow().isoformat(), datetime.utcnow().isoformat()],
            'file_name': ['upload_batch_1.csv', 'upload_batch_2.csv'],
            'row_number': [5, 12],
            'error_desc': ['Invalid mobile number format', 'Missing required PAN number']
        })
        output = io.BytesIO()
        df_errors.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        current_app.logger.info("Generated mock error data Excel file content.")
        return output.getvalue()


# --- Service Manager (Optional, but good for centralizing service access) ---
class ServiceManager:
    """
    A central manager to initialize and provide access to all services.
    This helps in dependency injection (e.g., passing the db session).
    """
    def __init__(self, db_session=None):
        self.customer_service = CustomerService(db_session)
        self.ingestion_service = IngestionService(db_session)
        self.offer_service = OfferService(db_session)
        self.event_service = EventService(db_session)
        self.report_service = ReportService(db_session)
        # Add other services as they are created.

# This `__init__.py` file defines the service classes and a potential ServiceManager.
# The actual instantiation of `ServiceManager` (with a real `db_session`)
# would typically happen in `backend/app.py` or `backend/routes/__init__.py`
# and then passed to route handlers or made available via Flask's `current_app`.