import datetime
from sqlalchemy import and_
from backend.app import db
from backend.models import Customer, Offer, Event


def update_offer_statuses():
    """
    Updates the status of offers based on defined business logic:
    - Marks offers as 'Expired' for non-journey started customers if offer end date has passed (FR41).
    - Marks offers as 'Expired' for journey started customers if their associated LAN validity is over (FR43).
    """
    current_date = datetime.date.today()
    updated_count = 0

    print(f"Starting offer status update task at {datetime.datetime.now()}")

    try:
        # FR41: Mark offers as expired for non-journey started customers
        # (i.e., customers.loan_application_number is NULL)
        # whose offer end_date has passed.
        offers_to_expire_non_journey = db.session.query(Offer).join(Customer).filter(
            and_(
                Offer.offer_status == 'Active',
                Offer.end_date < current_date,
                Customer.loan_application_number.is_(None)
            )
        ).all()

        for offer in offers_to_expire_non_journey:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.datetime.now()
            updated_count += 1
            print(f"  Expired offer {offer.offer_id} for non-journey customer {offer.customer_id} (FR41)")

        # FR43: Mark offers as expired for journey started customers
        # (i.e., customers.loan_application_number is NOT NULL)
        # whose LAN validity is over.
        # A LAN is considered "over" if there exists a terminal event
        # (LOAN_REJECTED, LOAN_DISBURSED, LOAN_EXPIRED) for that specific LAN
        # associated with the customer.
        offers_to_expire_journey = db.session.query(Offer).join(Customer).filter(
            and_(
                Offer.offer_status == 'Active',
                Customer.loan_application_number.isnot(None),
                # Check if a terminal event exists for the customer's current LAN
                db.session.query(Event).filter(
                    and_(
                        Event.customer_id == Customer.customer_id,  # Correlate by customer_id
                        # Assuming 'loan_application_number' is stored in event_details JSONB
                        Event.event_details.op('->>')('loan_application_number') == Customer.loan_application_number,
                        Event.event_type.in_(['LOAN_REJECTED', 'LOAN_DISBURSED', 'LOAN_EXPIRED'])
                    )
                ).exists()
            )
        ).all()

        for offer in offers_to_expire_journey:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.datetime.now()
            updated_count += 1
            print(f"  Expired offer {offer.offer_id} for journey customer {offer.customer_id} (FR43 - LAN over)")

        db.session.commit()
        print(f"Offer status update completed. Total {updated_count} offers updated.")

    except Exception as e:
        db.session.rollback()
        print(f"Error updating offer statuses: {e}")
        # Re-raise the exception to ensure scheduler/caller knows about the failure
        raise


if __name__ == "__main__":
    # This block is for local testing/execution.
    # In a real Flask application, this task would typically be run via a Flask CLI command
    # or a scheduled job that sets up the application context.
    try:
        from backend.app import create_app
        app = create_app()
        with app.app_context():
            update_offer_statuses()
    except ImportError:
        print("Could not import Flask app components. Ensure you are running this within a Flask project setup.")
        print("This script is designed to be part of a larger Flask application.")
    except Exception as e:
        print(f"An error occurred during standalone execution: {e}")