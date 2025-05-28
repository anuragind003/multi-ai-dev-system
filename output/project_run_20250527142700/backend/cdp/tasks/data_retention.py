import datetime
from sqlalchemy import and_, not_
from sqlalchemy.sql import exists, select

# Assuming models and db object are accessible from a central point,
# e.g., from backend.models or passed in.
# For a task file, it's common to import db and models directly.
from backend.models import db, Customer, Offer, OfferHistory, Event, Campaign

def clean_main_cdp_data():
    """
    Deletes customer, offer, event, and campaign data older than 3 months.
    Adheres to FR29 and NFR11: "All the data should be maintained in LTFS Offer CDP
    for previous 3 months before deletion from CDP."

    Deletion order respects foreign key dependencies and ensures customer data
    is retained if there's any recent associated activity.
    1. Events older than 3 months.
    2. Offers older than 3 months.
    3. Campaigns older than 3 months.
    4. Customers (only if created more than 3 months ago AND have no associated
       offers or events created/recorded within the last 3 months).
    """
    three_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
    print(f"Starting main CDP data retention cleanup for data older than: {three_months_ago}")

    try:
        # 1. Delete old events
        # Using synchronize_session=False for bulk deletion performance
        deleted_events_count = db.session.query(Event).filter(
            Event.event_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_events_count} old event records.")

        # 2. Delete old offers
        deleted_offers_count = db.session.query(Offer).filter(
            Offer.created_at < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_offers_count} old offer records.")

        # 3. Delete old campaigns
        deleted_campaigns_count = db.session.query(Campaign).filter(
            Campaign.created_at < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_campaigns_count} old campaign records.")

        # 4. Delete old customers
        # A customer record is deleted only if:
        #   a) The customer record itself was created more than 3 months ago.
        #   b) There are no associated offers created within the last 3 months.
        #   c) There are no associated events recorded within the last 3 months.
        # This ensures that a customer profile is retained if there's any recent activity.
        deleted_customers_count = db.session.query(Customer).filter(
            Customer.created_at < three_months_ago,
            # Check if no recent offers exist for this customer
            ~exists().where(and_(
                Offer.customer_id == Customer.customer_id,
                Offer.created_at >= three_months_ago
            )),
            # Check if no recent events exist for this customer
            ~exists().where(and_(
                Event.customer_id == Customer.customer_id,
                Event.event_timestamp >= three_months_ago
            ))
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_customers_count} old customer records.")

        db.session.commit()
        print("Main CDP data retention cleanup completed successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during main CDP data retention cleanup: {e}")
        raise # Re-raise the exception to signal failure to a scheduler

def clean_offer_history():
    """
    Deletes offer history data older than 6 months.
    Adheres to FR20 and NFR10: "Offer history shall be maintained for 6 months."
    """
    six_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=180)
    print(f"Starting offer history retention cleanup for data older than: {six_months_ago}")

    try:
        deleted_history_count = db.session.query(OfferHistory).filter(
            OfferHistory.status_change_date < six_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_history_count} old offer history records.")

        db.session.commit()
        print("Offer history retention cleanup completed successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during offer history retention cleanup: {e}")
        raise # Re-raise the exception to signal failure to a scheduler