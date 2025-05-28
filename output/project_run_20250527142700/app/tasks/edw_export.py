from flask import current_app
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

# Assuming db and models are defined in app.extensions and app.models respectively
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, Campaign

def export_cdp_data_to_edw():
    """
    Task to extract all relevant CDP data and prepare it for transfer to EDW.
    FR23: The system shall pass all data, including campaign data, from LTFS Offer CDP to EDW daily by day end.
    NFR8: The system shall perform daily data transfer from LTFS Offer CDP to EDW by day end.
    This function simulates the extraction and logging of data for EDW.
    The actual transfer mechanism (e.g., S3, SFTP, direct DB link) is external to this function.
    """
    logger = current_app.logger
    logger.info("Starting daily CDP data export to EDW...")

    try:
        engine = db.session.bind
        if not engine:
            logger.error("Database engine not bound to session. Cannot export to EDW.")
            raise RuntimeError("Database engine not bound for EDW export.")

        # Extract data for Customers
        # Using .statement to get the raw SQL query from the SQLAlchemy query object
        customers_query = db.session.query(Customer).statement
        customers_df = pd.read_sql(customers_query, engine)
        logger.info(f"Extracted {len(customers_df)} customer records for EDW.")

        # Extract data for Offers
        offers_query = db.session.query(Offer).statement
        offers_df = pd.read_sql(offers_query, engine)
        logger.info(f"Extracted {len(offers_df)} offer records for EDW.")

        # Extract data for Customer Events
        # As per FR23 "pass all data", we extract all events.
        # In a production system with high event volume, this might need to be
        # optimized to only extract events from the last day/period.
        events_query = db.session.query(CustomerEvent).statement
        events_df = pd.read_sql(events_query, engine)
        logger.info(f"Extracted {len(events_df)} customer event records for EDW.")

        # Extract data for Campaigns
        campaigns_query = db.session.query(Campaign).statement
        campaigns_df = pd.read_sql(campaigns_query, engine)
        logger.info(f"Extracted {len(campaigns_df)} campaign records for EDW.")

        # In a real scenario, these DataFrames would then be written to a target EDW system.
        # E.g., df.to_csv('s3://edw-bucket/customers.csv'), or pushed via an API.
        # For this simulation, we just log the completion and return summary.

        logger.info("CDP data extraction for EDW completed. Ready for transfer.")
        return {
            "status": "success",
            "message": "Data extracted for EDW transfer",
            "counts": {
                "customers": len(customers_df),
                "offers": len(offers_df),
                "events": len(events_df),
                "campaigns": len(campaigns_df)
            }
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error during CDP data export to EDW: {e}")
        # It's good practice to rollback the session in case of an ORM-related error,
        # though pd.read_sql typically operates on a connection and doesn't affect
        # the session's transaction state directly unless it's part of a larger transaction.
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during CDP data export to EDW: {e}")
        raise