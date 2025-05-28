import os
import logging
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import IntegrityError, OperationalError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
MAS_DB_URL = os.getenv("MAS_DB_URL")
CDP_DB_URL = os.getenv("CDP_DB_URL")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Engines ---
mas_engine = None
cdp_engine = None

def setup_db_connections():
    """Sets up SQLAlchemy engines for MAS and CDP databases."""
    global mas_engine, cdp_engine
    try:
        if not MAS_DB_URL:
            raise ValueError("MAS_DB_URL environment variable not set.")
        if not CDP_DB_URL:
            raise ValueError("CDP_DB_URL environment variable not set.")

        mas_engine = create_engine(MAS_DB_URL)
        cdp_engine = create_engine(CDP_DB_URL)

        # Test connections
        with mas_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to MAS database.")

        with cdp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to CDP database.")

    except (ValueError, OperationalError) as e:
        logger.error(f"Database connection error: {e}")
        raise

def close_db_connections():
    """Closes database connections."""
    if mas_engine:
        mas_engine.dispose()
        logger.info("MAS database connection disposed.")
    if cdp_engine:
        cdp_engine.dispose()
        logger.info("CDP database connection disposed.")

# --- Helper Functions ---

def get_cdp_customer_id(cdp_conn, mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None):
    """
    Checks if a customer exists in CDP based on unique identifiers and returns their customer_id.
    Prioritizes identifiers in the order: mobile, pan, aadhaar, ucid.
    """
    query_parts = []
    params = {}

    if mobile_number:
        query_parts.append("mobile_number = :mobile_number")
        params['mobile_number'] = mobile_number
    if pan_number:
        query_parts.append("pan_number = :pan_number")
        params['pan_number'] = pan_number
    if aadhaar_number:
        query_parts.append("aadhaar_number = :aadhaar_number")
        params['aadhaar_number'] = aadhaar_number
    if ucid_number:
        query_parts.append("ucid_number = :ucid_number")
        params['ucid_number'] = ucid_number

    if not query_parts:
        return None

    query = f"SELECT customer_id FROM customers WHERE {' OR '.join(query_parts)}"
    result = cdp_conn.execute(text(query), params).fetchone()
    return result[0] if result else None

def table_exists(engine, table_name):
    """Checks if a table exists in the given database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

# --- Migration Logic ---

def migrate_customers():
    """
    Migrates customer data from MAS to CDP.
    Handles basic deduplication based on unique identifiers (mobile, pan, aadhaar, ucid).
    Returns a dictionary mapping MAS customer IDs to CDP customer UUIDs.
    """
    logger.info("Starting customer data migration...")
    mas_customer_to_cdp_customer_map = {}
    migrated_count = 0
    skipped_count = 0
    error_count = 0

    # --- ASSUMPTION: MAS Customer Table Name and Columns ---
    # The BRD states that MAS table names and columns will be shared.
    # For now, we use placeholders. Adjust these based on actual MAS schema.
    MAS_CUSTOMER_TABLE = "mas_customer_base" # Example MAS customer table name
    MAS_CUSTOMER_COLUMNS = [ # Example MAS customer columns
        "mas_customer_id", "mobile_number", "pan_number", "aadhaar_number",
        "ucid_number", "is_dnd", "segment", "other_attributes_json"
    ]
    # --- END ASSUMPTION ---

    if not table_exists(mas_engine, MAS_CUSTOMER_TABLE):
        logger.error(f"MAS customer table '{MAS_CUSTOMER_TABLE}' not found. Skipping customer migration.")
        return {}

    try:
        with mas_engine.connect() as mas_conn:
            # Fetch all customers from MAS
            mas_customers_result = mas_conn.execute(text(f"SELECT {', '.join(MAS_CUSTOMER_COLUMNS)} FROM {MAS_CUSTOMER_TABLE}")).fetchall()
            logger.info(f"Found {len(mas_customers_result)} records in MAS customer table.")

        with cdp_engine.connect() as cdp_conn:
            # Start a transaction for the entire customer migration batch
            with cdp_conn.begin():
                for mas_customer_row in mas_customers_result:
                    mas_data = dict(zip(MAS_CUSTOMER_COLUMNS, mas_customer_row))
                    mas_customer_id = mas_data["mas_customer_id"]

                    try:
                        # Check if customer already exists in CDP based on unique identifiers
                        existing_cdp_id = get_cdp_customer_id(
                            cdp_conn,
                            mobile_number=mas_data.get("mobile_number"),
                            pan_number=mas_data.get("pan_number"),
                            aadhaar_number=mas_data.get("aadhaar_number"),
                            ucid_number=mas_data.get("ucid_number")
                        )

                        if existing_cdp_id:
                            # Customer already exists, use existing ID and map MAS ID to it
                            cdp_customer_id = existing_cdp_id
                            mas_customer_to_cdp_customer_map[mas_customer_id] = cdp_customer_id
                            skipped_count += 1
                            logger.debug(f"Customer with MAS ID {mas_customer_id} already exists in CDP (CDP ID: {cdp_customer_id}). Skipping insertion.")
                            # In a more complex scenario, you might update existing CDP record here
                            # with MAS data if MAS is considered the primary source of truth for base data.
                        else:
                            # Insert new customer
                            cdp_customer_id = uuid.uuid4()
                            insert_query = text("""
                                INSERT INTO customers (
                                    customer_id, mobile_number, pan_number, aadhaar_number,
                                    ucid_number, is_dnd, segment, attributes, created_at, updated_at
                                ) VALUES (
                                    :customer_id, :mobile_number, :pan_number, :aadhaar_number,
                                    :ucid_number, :is_dnd, :segment, :attributes, :created_at, :updated_at
                                )
                            """)
                            cdp_conn.execute(insert_query, {
                                "customer_id": cdp_customer_id,
                                "mobile_number": mas_data.get("mobile_number"),
                                "pan_number": mas_data.get("pan_number"),
                                "aadhaar_number": mas_data.get("aadhaar_number"),
                                "ucid_number": mas_data.get("ucid_number"),
                                "is_dnd": mas_data.get("is_dnd", False), # Default to False if not present
                                "segment": mas_data.get("segment"),
                                "attributes": mas_data.get("other_attributes_json", {}), # Assuming JSONB
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            })
                            mas_customer_to_cdp_customer_map[mas_customer_id] = cdp_customer_id
                            migrated_count += 1
                            logger.debug(f"Migrated MAS customer {mas_customer_id} to CDP customer {cdp_customer_id}")

                    except IntegrityError as e:
                        # This error means a unique constraint was violated during insert
                        # This should ideally be caught by get_cdp_customer_id, but can happen in race conditions
                        error_count += 1
                        logger.warning(f"Integrity error for MAS customer {mas_customer_id}: {e}. Skipping record.")
                        # No explicit rollback needed here, as the outer transaction will handle it
                        # or the specific statement failed and the transaction is still active.
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error processing MAS customer {mas_customer_id}: {e}")
            # The 'with cdp_conn.begin():' block will automatically commit if no exceptions,
            # or rollback if an exception propagates.
            logger.info(f"Customer migration complete. Migrated: {migrated_count}, Skipped (existing): {skipped_count}, Errors: {error_count}")
            return mas_customer_to_cdp_customer_map

    except Exception as e:
        logger.error(f"An unexpected error occurred during customer migration: {e}")
        return {}

def migrate_offers(mas_customer_to_cdp_customer_map):
    """
    Migrates offer data from MAS to CDP.
    Requires a mapping of MAS customer IDs to CDP customer UUIDs.
    """
    logger.info("Starting offer data migration...")
    migrated_count = 0
    skipped_count = 0
    error_count = 0

    # --- ASSUMPTION: MAS Offer Table Name and Columns ---
    # The BRD states that MAS table names and columns will be shared.
    # For now, we use placeholders. Adjust these based on actual MAS schema.
    MAS_OFFER_TABLE = "mas_offers_data" # Example MAS offer table name
    MAS_OFFER_COLUMNS = [ # Example MAS offer columns
        "mas_offer_id", "mas_customer_id", "source_offer_id", "offer_type",
        "offer_status", "propensity", "loan_application_number", "valid_until",
        "source_system", "channel"
    ]
    # --- END ASSUMPTION ---

    if not table_exists(mas_engine, MAS_OFFER_TABLE):
        logger.error(f"MAS offer table '{MAS_OFFER_TABLE}' not found. Skipping offer migration.")
        return

    if not mas_customer_to_cdp_customer_map:
        logger.warning("No customer mapping available. Cannot migrate offers without linked customers.")
        return

    try:
        with mas_engine.connect() as mas_conn:
            # Fetch all offers from MAS
            mas_offers_result = mas_conn.execute(text(f"SELECT {', '.join(MAS_OFFER_COLUMNS)} FROM {MAS_OFFER_TABLE}")).fetchall()
            logger.info(f"Found {len(mas_offers_result)} records in MAS offer table.")

        with cdp_engine.connect() as cdp_conn:
            # Start a transaction for the entire offer migration batch
            with cdp_conn.begin():
                for mas_offer_row in mas_offers_result:
                    mas_data = dict(zip(MAS_OFFER_COLUMNS, mas_offer_row))
                    mas_offer_id = mas_data["mas_offer_id"]
                    mas_customer_id = mas_data["mas_customer_id"]

                    cdp_customer_id = mas_customer_to_cdp_customer_map.get(mas_customer_id)

                    if not cdp_customer_id:
                        skipped_count += 1
                        logger.warning(f"Skipping MAS offer {mas_offer_id}: No corresponding CDP customer found for MAS customer ID {mas_customer_id}. This MAS customer might have been skipped during customer migration due to existing data or errors.")
                        continue

                    try:
                        cdp_offer_id = uuid.uuid4()
                        insert_query = text("""
                            INSERT INTO offers (
                                offer_id, customer_id, source_offer_id, offer_type,
                                offer_status, propensity, loan_application_number, valid_until,
                                source_system, channel, is_duplicate, created_at, updated_at
                            ) VALUES (
                                :offer_id, :customer_id, :source_offer_id, :offer_type,
                                :offer_status, :propensity, :loan_application_number, :valid_until,
                                :source_system, :channel, :is_duplicate, :created_at, :updated_at
                            )
                        """)
                        cdp_conn.execute(insert_query, {
                            "offer_id": cdp_offer_id,
                            "customer_id": cdp_customer_id,
                            "source_offer_id": mas_data.get("source_offer_id"),
                            "offer_type": mas_data.get("offer_type"),
                            "offer_status": mas_data.get("offer_status"),
                            "propensity": mas_data.get("propensity"),
                            "loan_application_number": mas_data.get("loan_application_number"),
                            "valid_until": mas_data.get("valid_until"),
                            "source_system": mas_data.get("source_system", "MAS"), # Default to MAS if not specified
                            "channel": mas_data.get("channel"),
                            "is_duplicate": False, # Initial migration, CDP's deduplication service will handle this later
                            "created_at": datetime.now(),
                            "updated_at": datetime.now()
                        })
                        migrated_count += 1
                        logger.debug(f"Migrated MAS offer {mas_offer_id} to CDP offer {cdp_offer_id}")

                    except IntegrityError as e:
                        error_count += 1
                        logger.warning(f"Integrity error for MAS offer {mas_offer_id}: {e}. Skipping record.")
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error processing MAS offer {mas_offer_id}: {e}")
            # The 'with cdp_conn.begin():' block will automatically commit if no exceptions,
            # or rollback if an exception propagates.
            logger.info(f"Offer migration complete. Migrated: {migrated_count}, Skipped: {skipped_count}, Errors: {error_count}")

    except Exception as e:
        logger.error(f"An unexpected error occurred during offer migration: {e}")

# --- Main Execution ---

if __name__ == "__main__":
    logger.info("Starting MAS data migration script...")
    try:
        setup_db_connections()

        # Step 1: Migrate Customers and get the mapping of MAS_ID to CDP_UUID
        customer_id_map = migrate_customers()

        # Step 2: Migrate Offers using the customer mapping
        if customer_id_map:
            migrate_offers(customer_id_map)
        else:
            logger.warning("Customer migration failed or no customers found. Skipping offer migration.")

        logger.info("MAS data migration script finished successfully.")

    except Exception as e:
        logger.critical(f"Script terminated due to a critical error: {e}")
    finally:
        close_db_connections()