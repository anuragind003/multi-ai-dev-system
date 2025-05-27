import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

# In a typical Flask-SQLAlchemy application, models would be defined in a separate
# `models.py` file and imported. The `db` object would be initialized
# from `flask_sqlalchemy.SQLAlchemy`.
# For this exercise, we define a minimal Base and models here for self-containment
# to make the code runnable as a standalone service file.

# --- Start of simulated Flask-SQLAlchemy setup for models ---
Base = declarative_base()

class Customer(Base):
    """
    SQLAlchemy model for the 'customers' table.
    Minimal definition required for ForeignKey relationship with Event.
    """
    __tablename__ = 'customers'
    customer_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String, unique=True)
    pan_number = Column(String, unique=True)
    aadhaar_number = Column(String, unique=True)
    ucid_number = Column(String, unique=True)
    loan_application_number = Column(String, unique=True)
    dnd_flag = Column(Boolean, default=False)
    segment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Customer(id='{self.customer_id}', mobile='{self.mobile_number}')>"

class Event(Base):
    """
    SQLAlchemy model for the 'events' table.
    Stores various customer interaction and application journey events.
    """
    __tablename__ = 'events'
    event_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey('customers.customer_id'), nullable=False)
    event_type = Column(String, nullable=False)  # e.g., 'SMS_SENT', 'EKYC_ACHIEVED', 'LOAN_LOGIN'
    event_source = Column(String, nullable=False)  # e.g., 'Moengage', 'LOS', 'E-aggregator'
    event_timestamp = Column(DateTime, default=datetime.utcnow)
    event_details = Column(JSONB)  # Flexible storage for event-specific data
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (f"<Event(id='{self.event_id}', type='{self.event_type}', "
                f"source='{self.event_source}', customer_id='{self.customer_id}')")

# --- End of simulated Flask-SQLAlchemy setup for models ---


class EventTrackingService:
    """
    Service class for tracking and managing customer events.
    Handles recording various types of events from different sources
    and retrieving event history.
    """
    def __init__(self, db_session):
        """
        Initializes the EventTrackingService with a database session.

        Args:
            db_session: An SQLAlchemy session object for database interactions.
        """
        self.db_session = db_session

    def record_event(self, customer_id: str, event_type: str, event_source: str,
                     event_timestamp: datetime = None, event_details: dict = None) -> dict:
        """
        Records a new event in the database.

        Args:
            customer_id (str): The UUID of the customer associated with the event.
            event_type (str): The type of event (e.g., 'SMS_SENT', 'EKYC_ACHIEVED', 'LOAN_LOGIN').
            event_source (str): The source system of the event (e.g., 'Moengage', 'LOS', 'E-aggregator').
            event_timestamp (datetime, optional): The timestamp of the event. Defaults to current UTC time.
            event_details (dict, optional): A dictionary of additional event-specific details. Defaults to None.

        Returns:
            dict: A dictionary containing the recorded event's ID and status, or an error message.
        """
        if not customer_id or not event_type or not event_source:
            return {"status": "error", "message": "Customer ID, event type, and event source are required."}

        try:
            # Convert customer_id string to UUID object for database storage
            customer_uuid = uuid.UUID(customer_id)

            new_event = Event(
                event_id=uuid.uuid4(),
                customer_id=customer_uuid,
                event_type=event_type,
                event_source=event_source,
                event_timestamp=event_timestamp if event_timestamp else datetime.utcnow(),
                event_details=event_details if event_details is not None else {}
            )
            self.db_session.add(new_event)
            self.db_session.commit()
            return {"status": "success", "event_id": str(new_event.event_id)}
        except ValueError:
            self.db_session.rollback()
            return {"status": "error", "message": "Invalid customer_id format (must be a valid UUID)."}
        except SQLAlchemyError as e:
            self.db_session.rollback()
            # In a production environment, use a proper logging framework
            print(f"Database error recording event: {e}")
            return {"status": "error", "message": "Failed to record event due to a database error."}
        except Exception as e:
            self.db_session.rollback()
            print(f"An unexpected error occurred while recording event: {e}")
            return {"status": "error", "message": "An unexpected error occurred while recording the event."}

    def get_customer_events(self, customer_id: str, limit: int = 100) -> list:
        """
        Retrieves a list of events for a given customer, ordered by timestamp descending.

        Args:
            customer_id (str): The UUID of the customer.
            limit (int, optional): Maximum number of events to retrieve. Defaults to 100.

        Returns:
            list: A list of dictionaries, each representing an event.
                  Returns an empty list if customer_id is invalid or no events found.
        """
        if not customer_id:
            return []

        try:
            customer_uuid = uuid.UUID(customer_id)
            events = self.db_session.query(Event).filter_by(customer_id=customer_uuid)\
                                     .order_by(Event.event_timestamp.desc())\
                                     .limit(limit).all()

            result = []
            for event in events:
                result.append({
                    "event_id": str(event.event_id),
                    "customer_id": str(event.customer_id),
                    "event_type": event.event_type,
                    "event_source": event.event_source,
                    "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                    "event_details": event.event_details
                })
            return result
        except ValueError:
            # Invalid UUID format for customer_id
            return []
        except SQLAlchemyError as e:
            print(f"Database error retrieving events for customer {customer_id}: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while retrieving events: {e}")
            return []

    def record_application_status_update(self, loan_application_number: str, customer_id: str,
                                         current_stage: str, status_timestamp: datetime = None) -> dict:
        """
        Records an application status update event, typically from LOS or E-aggregators.
        This maps directly to the /api/status-updates endpoint's logic.

        Args:
            loan_application_number (str): The loan application number associated with the update.
            customer_id (str): The UUID of the customer.
            current_stage (str): The current stage of the application (e.g., 'login', 'bureau check', 'eKYC').
            status_timestamp (datetime, optional): The timestamp of the status update. Defaults to current UTC time.

        Returns:
            dict: A dictionary containing the recorded event's ID and status, or an error message.
        """
        event_details = {
            "loan_application_number": loan_application_number,
            "current_stage": current_stage
        }
        # As per FR26, application stage data is from LOS.
        event_type = f"APP_STAGE_{current_stage.upper().replace(' ', '_')}"
        return self.record_event(
            customer_id=customer_id,
            event_type=event_type,
            event_source="LOS",
            event_timestamp=status_timestamp,
            event_details=event_details
        )

    def record_sms_event(self, customer_id: str, sms_status: str, campaign_id: str = None,
                         message_id: str = None, sms_timestamp: datetime = None) -> dict:
        """
        Records an SMS event (sent, delivered, click) from Moengage.

        Args:
            customer_id (str): The UUID of the customer.
            sms_status (str): The status of the SMS (e.g., 'SENT', 'DELIVERED', 'CLICKED').
            campaign_id (str, optional): The ID of the campaign the SMS belongs to.
            message_id (str, optional): The unique ID of the SMS message.
            sms_timestamp (datetime, optional): The timestamp of the SMS event. Defaults to current UTC time.

        Returns:
            dict: A dictionary containing the recorded event's ID and status, or an error message.
        """
        event_details = {
            "sms_status": sms_status,
            "campaign_id": campaign_id,
            "message_id": message_id
        }
        # As per FR24, SMS event data is from Moengage.
        event_type = f"SMS_{sms_status.upper()}"
        return self.record_event(
            customer_id=customer_id,
            event_type=event_type,
            event_source="Moengage",
            event_timestamp=sms_timestamp,
            event_details=event_details
        )

    def record_conversion_event(self, customer_id: str, conversion_type: str,
                                loan_application_number: str = None, conversion_timestamp: datetime = None) -> dict:
        """
        Records a conversion event (e.g., EKYC achieved, Disbursement).

        Args:
            customer_id (str): The UUID of the customer.
            conversion_type (str): The type of conversion (e.g., 'EKYC_ACHIEVED', 'DISBURSEMENT').
            loan_application_number (str, optional): The associated loan application number.
            conversion_timestamp (datetime, optional): The timestamp of the conversion. Defaults to current UTC time.

        Returns:
            dict: A dictionary containing the recorded event's ID and status, or an error message.
        """
        event_details = {
            "conversion_type": conversion_type,
            "loan_application_number": loan_application_number
        }
        # As per FR25, conversion data is from LOS/Moengage.
        # Assuming LOS for EKYC/Disbursement, but could be Moengage for other conversion types.
        event_source = "LOS" if conversion_type.upper() in ["EKYC_ACHIEVED", "DISBURSEMENT"] else "Moengage"
        event_type = f"CONVERSION_{conversion_type.upper()}"
        return self.record_event(
            customer_id=customer_id,
            event_type=event_type,
            event_source=event_source,
            event_timestamp=conversion_timestamp,
            event_details=event_details
        )