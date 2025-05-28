import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from uuid import UUID # For type hinting if needed, or for explicit UUID conversion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Load environment variables for database connections
# In a production environment, these would be set securely (e.g., Kubernetes secrets, AWS Secrets Manager)
# For local development, use a .env file and python-dotenv
CDP_DATABASE_URL = os.getenv('CDP_DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')
MAS_DATABASE_URL = os.getenv('MAS_DATABASE_URL', 'postgresql://mas_user:mas_password@localhost:5433/mas_db')

# --- Flask App and CDP Database Setup ---
# Create a minimal Flask app instance to provide application context for Flask-SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = CDP_DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress warning

db = SQLAlchemy(app)

# Import models after db is initialized to avoid circular imports if models depend on db.
# This script assumes 'app' is a discoverable package (e.g., by running from project root
# or setting PYTHONPATH). If 'app' is not found, the script will exit with an error.
try:
    from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog
    logger.info("Successfully imported models from app.models.")
except ImportError as e:
    logger.error(f"Error importing Flask app components: {e}")
    logger.error("Please ensure you are running this script from the project root or have configured PYTHONPATH correctly.")
    logger.error("Example: `export PYTHONPATH=$(pwd)` from your project root before running `python scripts/initial_mas_migration.py`.")
    # Exit if models cannot be imported, as the script cannot function without them.
    exit(1)

# --- MAS Database Connection ---
# Use SQLAlchemy's create_engine for direct connection to MAS DB, as it's an external system.
try:
    mas_engine = create_engine(MAS_DATABASE_URL)
    MASSession = sessionmaker(bind=mas_engine)
    logger.info("Successfully connected to MAS database.")
except Exception as e:
    logger.error(f"Failed to connect to MAS database at {MAS_DATABASE_URL}: {e}")
    logger.error("Please ensure the MAS database is accessible and connection details are correct.")
    exit(1) # Exit if MAS connection is critical for migration

def migrate_mas_data():
    """
    Performs a one-time data migration from the MAS database to new tables in the CDP database.
    This addresses Functional Requirements FR11 (one-time data migration) and FR12 (one-time base data).

    Assumes MAS tables 'mas_customer_details' and 'mas_loan_offers' exist
    with relevant columns that can be mapped to CDP's 'customers' and 'offers' tables.
    The exact column names are placeholders and should be adjusted based on actual MAS schema.
    """
    logger.info("Starting MAS data migration to CDP...")

    total_customers_migrated = 0
    total_offers_migrated = 0
    # Map MAS customer identifier (e.g., mobile number) to new CDP customer_id (UUID)
    customer_id_map = {}

    # Ensure operations run within the Flask application context
    with app.app_context():
        cdp_session = db.session
        mas_session = MASSession()

        try:
            # --- Migrate Customer Data ---
            logger.info("Migrating customer data from MAS...")
            # Placeholder query for MAS customer details. Adjust column names as per actual MAS schema.
            mas_customers_query = text("""
                SELECT
                    mas_mobile_no,
                    mas_pan_no,
                    mas_aadhaar_no,
                    mas_ucid,
                    mas_prev_loan_app_no,
                    mas_customer_segment,
                    mas_is_dnd_flag,
                    mas_other_attributes_jsonb -- Assuming this column exists and is JSONB compatible
                FROM mas_customer_details
                WHERE mas_mobile_no IS NOT NULL -- Mobile number is a primary identifier in CDP
                ORDER BY mas_mobile_no;
            """)
            mas_customer_records = mas_session.execute(mas_customers_query).fetchall()
            logger.info(f"Found {len(mas_customer_records)} customer records in MAS.")

            for i, record in enumerate(mas_customer_records):
                try:
                    # Basic validation: mobile number is mandatory for CDP customer
                    if not record.mas_mobile_no:
                        logger.warning(f"Skipping MAS customer record {i+1} due to missing mobile number.")
                        continue

                    # Deduplication logic during migration (FR2, FR3, FR4)
                    # Check if customer already exists in CDP based on any unique identifier
                    existing_customer = cdp_session.query(Customer).filter(
                        (Customer.mobile_number == record.mas_mobile_no) |
                        (Customer.pan == record.mas_pan_no and record.mas_pan_no is not None) |
                        (Customer.aadhaar_ref_number == record.mas_aadhaar_no and record.mas_aadhaar_no is not None) |
                        (Customer.ucid == record.mas_ucid and record.mas_ucid is not None) |
                        (Customer.previous_loan_app_number == record.mas_prev_loan_app_no and record.mas_prev_loan_app_no is not None)
                    ).first()

                    cdp_customer_id = None
                    if existing_customer:
                        logger.debug(f"Customer with mobile {record.mas_mobile_no} already exists in CDP (ID: {existing_customer.customer_id}). Using existing record.")
                        cdp_customer_id = existing_customer.customer_id
                        # In a more complex scenario, you might update existing customer attributes here.
                    else:
                        new_customer = Customer(
                            mobile_number=record.mas_mobile_no,
                            pan=record.mas_pan_no,
                            aadhaar_ref_number=record.mas_aadhaar_no,
                            ucid=record.mas_ucid,
                            previous_loan_app_number=record.mas_prev_loan_app_no,
                            customer_segment=record.mas_customer_segment,
                            is_dnd=record.mas_is_dnd_flag if record.mas_is_dnd_flag is not None else False,
                            customer_attributes=record.mas_other_attributes_jsonb # Ensure this is a dict/JSONB compatible
                        )
                        cdp_session.add(new_customer)
                        # Flush to get the generated UUID for the new customer
                        cdp_session.flush()
                        cdp_customer_id = new_customer.customer_id
                        total_customers_migrated += 1
                        logger.debug(f"Migrated new customer (ID: {cdp_customer_id}) from MAS mobile: {record.mas_mobile_no}")

                    # Store the mapping for offers
                    customer_id_map[record.mas_mobile_no] = cdp_customer_id

                except Exception as e:
                    logger.error(f"Error processing MAS customer record {i+1} (mobile: {record.mas_mobile_no}): {e}")
                    cdp_session.rollback() # Rollback current transaction for this record
                    continue # Continue to the next record

            cdp_session.commit() # Commit all successfully processed customers
            logger.info(f"Successfully migrated {total_customers_migrated} new customer records to CDP.")

            # --- Migrate Offer Data ---
            logger.info("Migrating offer data from MAS...")
            # Placeholder query for MAS loan offers. Adjust column names as per actual MAS schema.
            mas_offers_query = text("""
                SELECT
                    mas_offer_id,
                    mas_mobile_no,
                    mas_offer_type,
                    mas_offer_status,
                    mas_propensity_flag,
                    mas_offer_start_date,
                    mas_offer_end_date,
                    mas_loan_application_number,
                    mas_attribution_channel
                FROM mas_loan_offers
                WHERE mas_mobile_no IS NOT NULL; -- Ensure we can link to a CDP customer
            """)
            mas_offer_records = mas_session.execute(mas_offers_query).fetchall()
            logger.info(f"Found {len(mas_offer_records)} offer records in MAS.")

            for i, record in enumerate(mas_offer_records):
                try:
                    # Link offer to CDP customer_id using the map created earlier
                    cdp_customer_id = customer_id_map.get(record.mas_mobile_no)
                    if not cdp_customer_id:
                        logger.warning(f"Skipping MAS offer record {i+1} (MAS Offer ID: {record.mas_offer_id}) due to no corresponding customer found in CDP for mobile {record.mas_mobile_no}.")
                        continue

                    # Create new Offer record
                    new_offer = Offer(
                        customer_id=cdp_customer_id,
                        offer_type=record.mas_offer_type,
                        offer_status=record.mas_offer_status,
                        propensity_flag=record.mas_propensity_flag,
                        offer_start_date=record.mas_offer_start_date,
                        offer_end_date=record.mas_offer_end_date,
                        loan_application_number=record.mas_loan_application_number,
                        attribution_channel=record.mas_attribution_channel
                    )
                    cdp_session.add(new_offer)
                    total_offers_migrated += 1
                    logger.debug(f"Migrated offer (MAS ID: {record.mas_offer_id}) for CDP customer ID: {cdp_customer_id}")

                except Exception as e:
                    logger.error(f"Error processing MAS offer record {i+1} (MAS Offer ID: {record.mas_offer_id}, mobile: {record.mas_mobile_no}): {e}")
                    cdp_session.rollback() # Rollback current transaction for this record
                    continue # Continue to the next record

            cdp_session.commit() # Commit all successfully processed offers
            logger.info(f"Successfully migrated {total_offers_migrated} offer records to CDP.")

            logger.info("MAS data migration completed successfully.")

        except Exception as e:
            cdp_session.rollback() # Rollback any pending transactions on critical failure
            logger.critical(f"An unrecoverable error occurred during migration: {e}")
        finally:
            cdp_session.close()
            mas_session.close()
            logger.info("Database sessions closed.")

if __name__ == '__main__':
    # This block ensures the script can be run directly.
    # It will create a minimal Flask app context for database operations.
    logger.info("Executing initial MAS data migration script.")
    migrate_mas_data()
    logger.info("Initial MAS data migration script finished.")