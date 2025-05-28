import os
import sys
from datetime import datetime, timedelta
import csv
import json

# Add the project root to the sys.path to allow absolute imports
# Assuming this script is in backend/scripts/
# and app.py/config.py/models.py are in backend/
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, project_root)

from app import create_app, db
from models import Offer, Customer # Assuming Offer and Customer models are defined in models.py

# Configuration for the script
# In a real application, these would be loaded from environment variables or a config file
# For demonstration, we'll define a path for the output CSV file.
# In a production environment, this would likely be an API call to Offermart.
OFFERMART_FEED_FILE_PATH = os.path.join(project_root, 'data', 'offermart_reverse_feed.csv')

def get_offers_for_reverse_feed(app_context):
    """
    Retrieves offers from the CDP database that need to be sent back to Offermart.
    This includes offers originating from Offermart whose status has changed
    or are marked as duplicate, and have not been fed back since their last update.
    """
    with app_context:
        # Query offers that originated from Offermart and meet the criteria for an update:
        # 1. Their status is not 'Active' (i.e., 'Expired' or 'Inactive') OR they are marked as duplicate.
        # 2. They have not been fed to Offermart yet (fed_to_offermart_at is NULL)
        #    OR their 'updated_at' timestamp is more recent than 'fed_to_offermart_at'.
        offers_to_feed = db.session.query(Offer).filter(
            Offer.source_system == 'Offermart',
            (
                (Offer.offer_status != 'Active') |
                (Offer.is_duplicate == True)
            ),
            (
                (Offer.fed_to_offermart_at.is_(None)) |
                (Offer.fed_to_offermart_at < Offer.updated_at)
            )
        ).all()
        return offers_to_feed

def generate_offermart_feed_data(offers):
    """
    Generates a list of dictionaries, each representing an offer update
    to be sent to Offermart.
    """
    feed_data = []
    for offer in offers:
        # Prepare the data fields that Offermart would need to update its records.
        # This typically includes Offermart's original ID for the offer,
        # the current status, and any other relevant flags like 'is_duplicate'.
        feed_data.append({
            'cdp_offer_id': str(offer.offer_id), # CDP's internal offer ID
            'offermart_source_offer_id': offer.source_offer_id, # Offermart's original ID
            'cdp_customer_id': str(offer.customer_id), # CDP's internal customer ID
            'current_offer_status': offer.offer_status, # Current status in CDP (Active, Inactive, Expired)
            'is_cdp_duplicate': offer.is_duplicate, # Whether CDP marked it as duplicate
            'loan_application_number': offer.loan_application_number, # LAN, if applicable
            'valid_until': offer.valid_until.isoformat() if offer.valid_until else None,
            'cdp_last_updated_at': offer.updated_at.isoformat()
        })
    return feed_data

def send_feed_to_offermart(feed_data):
    """
    Simulates sending the generated feed data to Offermart.
    In a real scenario, this would involve an HTTP POST request to Offermart's API
    or writing to a secure shared file location/message queue.
    For this implementation, we simulate by writing to a CSV file.
    """
    if not feed_data:
        print("No data to send to Offermart.")
        return True

    print(f"Attempting to send {len(feed_data)} offer updates to Offermart...")

    try:
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(OFFERMART_FEED_FILE_PATH), exist_ok=True)

        with open(OFFERMART_FEED_FILE_PATH, 'w', newline='') as csvfile:
            fieldnames = feed_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(feed_data)
        print(f"Successfully generated Offermart reverse feed CSV at: {OFFERMART_FEED_FILE_PATH}")
        return True
    except Exception as e:
        print(f"Error writing Offermart reverse feed CSV: {e}")
        return False

    # Example of how an actual API call might look (requires 'requests' library):
    # import requests
    # OFFERMART_API_ENDPOINT = os.getenv('OFFERMART_API_ENDPOINT')
    # OFFERMART_API_KEY = os.getenv('OFFERMART_API_KEY') # For authentication
    # try:
    #     headers = {'Content-Type': 'application/json', 'X-API-Key': OFFERMART_API_KEY}
    #     response = requests.post(OFFERMART_API_ENDPOINT, json=feed_data, headers=headers)
    #     response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
    #     print(f"Successfully sent {len(feed_data)} offer updates to Offermart via API.")
    #     return True
    # except requests.exceptions.RequestException as e:
    #     print(f"Error sending data to Offermart API: {e}")
    #     return False

def update_offers_fed_status(app_context, offers):
    """
    Updates the `fed_to_offermart_at` timestamp for successfully fed offers in CDP.
    This marks them as processed for the reverse feed, preventing re-sending
    unless their `updated_at` timestamp changes again.
    """
    with app_context:
        for offer in offers:
            offer.fed_to_offermart_at = datetime.now()
        try:
            db.session.commit()
            print(f"Successfully updated fed status for {len(offers)} offers in CDP.")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating fed status for offers: {e}")

def main():
    """
    Main function to orchestrate the reverse feed process.
    Initializes the Flask application context, retrieves relevant offers,
    generates the feed data, simulates sending it to Offermart,
    and updates the CDP database.
    """
    print("Starting Offermart Reverse Feed script...")

    app = create_app()
    with app.app_context() as app_context:
        offers_to_feed = get_offers_for_reverse_feed(app_context)

        if not offers_to_feed:
            print("No relevant offer updates found to send to Offermart.")
            return

        print(f"Found {len(offers_to_feed)} offers to potentially feed back to Offermart.")

        feed_data = generate_offermart_feed_data(offers_to_feed)

        if send_feed_to_offermart(feed_data):
            # If sending was successful (or simulated successfully), update the CDP records
            update_offers_fed_status(app_context, offers_to_feed)
            print("Offermart Reverse Feed process completed successfully.")
        else:
            print("Offermart Reverse Feed process failed to send data.")

if __name__ == "__main__":
    main()