import datetime
from sqlalchemy import and_, not_
from sqlalchemy.sql import exists, select
# Assuming db and models are defined in backend.src.models
# and db is an instance of SQLAlchemy, and models are SQLAlchemy models.
from backend.src.models import db, Customer, Offer, OfferHistory, Event, Campaign

def clean_main_cdp_data():
    """
    Deletes customer, offer, event, and campaign data older than 3 months.
    Adheres to FR29 and NFR11: "All the data should be maintained in LTFS Offer CDP
    for previous 3 months before deletion from CDP."

    Deletion order is crucial due to foreign key constraints:
    1. Events (depend on Customer, Offer)
    2. Offers (depend on Customer)
    3. Campaigns (independent for deletion order)
    4. Customers (only if no recent associated offers or events)
    """
    # Calculate cutoff date: 3 months (approx 90 days) ago from UTC now
    three_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
    print(f"Starting main CDP data cleanup. Deleting data older than: {three_months_ago.isoformat()}")

    try:
        # 1. Delete old events
        # Events are linked to customers and offers. Delete them first.
        deleted_events_count = db.session.query(Event).filter(
            Event.event_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_events_count} old event records.")

        # 2. Delete old offers
        # Offers are linked to customers. Delete them after events.
        deleted_offers_count = db.session.query(Offer).filter(
            Offer.updated_at < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_offers_count} old offer records.")

        # 3. Delete old campaigns
        # Campaigns are independent of customers/offers for deletion order.
        deleted_campaigns_count = db.session.query(Campaign).filter(
            Campaign.campaign_date < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_campaigns_count} old campaign records.")

        # 4. Delete old customers
        # Only delete customers whose own record is old AND
        # who have no associated offers updated within the last 3 months AND
        # who have no associated events created within the last 3 months.
        # This ensures we don't delete a customer if they have any recent activity.

        # Subquery to find customer_ids that have offers updated within the last 3 months
        recent_offers_subquery = select(Offer.customer_id).filter(
            Offer.updated_at >= three_months_ago
        ).distinct()

        # Subquery to find customer_ids that have events created within the last 3 months
        recent_events_subquery = select(Event.customer_id).filter(
            Event.event_timestamp >= three_months_ago
        ).distinct()

        # Filter for customers whose own record is old AND
        # who are NOT in the list of customers with recent offers AND
        # who are NOT in the list of customers with recent events.
        deleted_customers_count = db.session.query(Customer).filter(
            Customer.updated_at < three_months_ago,
            ~Customer.customer_id.in_(recent_offers_subquery),
            ~Customer.customer_id.in_(recent_events_subquery)
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_customers_count} old customer records.")

        db.session.commit()
        print("Main CDP data cleanup completed successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during main CDP data cleanup: {e}")
        # Re-raise for external error handling if this is part of a larger job
        raise

def clean_offer_history():
    """
    Deletes offer history data older than 6 months.
    Adheres to FR20 and NFR10: "Offer history shall be maintained for 6 months."
    """
    # Calculate cutoff date: 6 months (approx 180 days) ago from UTC now
    six_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=180)
    print(f"Starting offer history cleanup. Deleting data older than: {six_months_ago.isoformat()}")

    try:
        deleted_history_count = db.session.query(OfferHistory).filter(
            OfferHistory.status_change_date < six_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_history_count} old offer history records.")

        db.session.commit()
        print("Offer history cleanup completed successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during offer history cleanup: {e}")
        # Re-raise for external error handling if this is part of a larger job
        raise

# This block is for demonstrating how these functions might be called.
# In a real Flask application, these would typically be invoked by a scheduled task runner
# (e.g., APScheduler, Celery Beat) that ensures the Flask application context
# and database connection are properly set up.
if __name__ == '__main__':
    print("This script defines data cleanup functions.")
    print("To execute them, ensure your Flask application context is active and database is configured.")
    print("Typically, these functions are called by a scheduled task runner.")
    # Example usage (requires Flask app context and db initialization):
    # from flask import Flask
    # from flask_sqlalchemy import SQLAlchemy
    # import os
    #
    # app = Flask(__name__)
    # app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    #     'DATABASE_URL',
    #     'postgresql://cdp_user:cdp_password@localhost:5432/cdp_db'
    # ).replace('postgres://', 'postgresql://')
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # db = SQLAlchemy(app)
    #
    # # In a real project, Customer, Offer, etc. would be imported from backend.src.models
    # # For this example to run standalone, you'd need dummy model definitions or a full app setup.
    #
    # with app.app_context():
    #     # db.create_all() # Uncomment to create tables for testing if needed
    #     clean_main_cdp_data()
    #     clean_offer_history()