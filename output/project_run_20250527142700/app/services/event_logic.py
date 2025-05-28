from app.extensions import db
from app.models import Customer, CustomerEvent
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from datetime import datetime
import uuid # Imported for clarity on UUID type, though not directly used for conversion here

def record_customer_event(
    customer_id: str,
    event_type: str,
    event_source: str,
    event_details: dict = None
) -> bool:
    """
    Records a customer event in the database.
    FR21: Stores event data from Moengage and LOS, avoiding DND Customers for Moengage events.
    FR22: Handles various event types (SMS sent, SMS delivered, SMS click, conversions,
          and application stages like login, bureau check, offer details, eKYC, Bank details,
          other details, e-sign).

    Args:
        customer_id (str): The UUID string of the customer for whom the event occurred.
        event_type (str): The specific type of event (e.g., 'SMS_SENT', 'CONVERSION',
                          'APP_STAGE_LOGIN', 'APP_STAGE_EKYC').
        event_source (str): The system from which the event originated ('Moengage', 'LOS').
        event_details (dict, optional): A dictionary containing additional event-specific data.
                                        This will be stored as JSONB in the database.
                                        Defaults to an empty dictionary if not provided.

    Returns:
        bool: True if the event was recorded successfully, False otherwise.
    """
    try:
        # Retrieve the customer by their primary key (customer_id)
        customer = Customer.query.get(customer_id)

        if not customer:
            current_app.logger.warning(f"Event recording failed: Customer with ID '{customer_id}' not found.")
            return False

        # FR21: Implement DND check for Moengage events
        if event_source.lower() == 'moengage' and customer.is_dnd:
            current_app.logger.info(
                f"Skipping Moengage event '{event_type}' for DND customer '{customer_id}'."
            )
            return False

        # Ensure event_details is a dictionary, even if None is passed
        details_to_store = event_details if event_details is not None else {}

        new_event = CustomerEvent(
            customer_id=customer.customer_id, # Use the UUID object from the fetched customer
            event_type=event_type,
            event_source=event_source,
            event_timestamp=datetime.utcnow(), # Store timestamp in UTC
            event_details=details_to_store
        )

        db.session.add(new_event)
        db.session.commit()
        current_app.logger.info(
            f"Successfully recorded event '{event_type}' from '{event_source}' for customer '{customer_id}'."
        )
        return True

    except SQLAlchemyError as e:
        db.session.rollback() # Rollback the session in case of a database error
        current_app.logger.error(f"Database error recording event for customer '{customer_id}': {e}")
        return False
    except Exception as e:
        db.session.rollback() # Rollback for any unexpected errors as well
        current_app.logger.error(f"An unexpected error occurred recording event for customer '{customer_id}': {e}")
        return False

def get_customer_events_by_customer_id(customer_id: str, limit: int = 100) -> list:
    """
    Retrieves a list of events for a given customer, ordered by the most recent first.
    This function supports the customer level view (FR36) to display application stages (FR22).

    Args:
        customer_id (str): The UUID string of the customer.
        limit (int): The maximum number of events to retrieve. Defaults to 100.

    Returns:
        list: A list of dictionaries, where each dictionary represents a customer event.
              Returns an empty list if no events are found for the customer or if an error occurs.
    """
    try:
        # Verify if the customer exists before querying for events
        customer_exists = db.session.query(Customer.customer_id).filter_by(customer_id=customer_id).first()
        if not customer_exists:
            current_app.logger.warning(f"No events found: Customer with ID '{customer_id}' does not exist.")
            return []

        # Query for customer events, ordered by timestamp descending
        events = CustomerEvent.query.filter_by(customer_id=customer_id)\
                                    .order_by(CustomerEvent.event_timestamp.desc())\
                                    .limit(limit)\
                                    .all()

        # Assuming the CustomerEvent model has a .to_dict() method to serialize
        # the ORM object into a dictionary suitable for API responses.
        return [event.to_dict() for event in events]
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error retrieving events for customer '{customer_id}': {e}")
        return []
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred retrieving events for customer '{customer_id}': {e}")
        return []