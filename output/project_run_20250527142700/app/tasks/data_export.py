import io
import pandas as pd
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, and_

# Assuming db and models are defined in app.extensions and app.models respectively
try:
    from app.extensions import db
    from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog
except ImportError:
    # This block is for standalone testing or if models/db are not yet fully set up.
    # In a real Flask application, these imports should resolve correctly when run
    # within the application context.
    print("WARNING: Could not import app.extensions or app.models. Using mock objects for local testing.")

    class MockDB:
        """Mock database object for standalone testing."""
        def session(self):
            return self
        def query(self, *args, **kwargs):
            return self
        def filter(self, *args, **kwargs):
            return self
        def all(self):
            return []
        def first(self):
            return None
        def add(self, *args, **kwargs):
            pass
        def commit(self):
            pass
        def rollback(self):
            pass
        def bind(self): # For pd.read_sql
            return None # In a real scenario, this would be the engine

    db = MockDB()

    # Mock model classes for standalone testing
    class MockCustomer:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def __repr__(self):
            return f"<MockCustomer {getattr(self, 'customer_id', 'N/A')}>"
    class MockOffer:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class MockCustomerEvent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class MockCampaign:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class MockDataIngestionLog:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    Customer = MockCustomer
    Offer = MockOffer
    CustomerEvent = MockCustomerEvent
    Campaign = MockCampaign
    DataIngestionLog = MockDataIngestionLog


def generate_moengage_data_for_export():
    """
    Generates a Pandas DataFrame containing data formatted for Moengage export.
    FR25: The system shall provide a screen for users to download the Moengage File in Excel or CSV format.
    FR39: The system shall provide a front-end utility for LTFS users to download the Moengage format file in .csv format.
    FR21: The system shall store event data from Moengage and LOS in the LTFS Offer CDP, avoiding DND Customers.
    """
    current_app.logger.info("Generating Moengage export data...")
    try:
        # Query active offers for non-DND customers
        # Assuming 'Active' offers are those relevant for campaigning
        # Join Customer and Offer tables
        query_results = db.session.query(
            Customer.mobile_number,
            Customer.customer_segment,
            Offer.offer_id,
            Offer.offer_type,
            Offer.propensity_flag,
            Offer.offer_end_date,
            Offer.attribution_channel
        ).join(Offer, Customer.customer_id == Offer.customer_id)\
        .filter(
            Customer.is_dnd == False,
            Offer.offer_status == 'Active',
            Offer.offer_end_date >= datetime.utcnow().date() # Only active and not expired offers
        ).all()

        # Convert query results to a list of dictionaries for DataFrame creation
        data = []
        for row in query_results:
            data.append({
                'mobile_number': row.mobile_number,
                'customer_segment': row.customer_segment,
                'offer_id': str(row.offer_id), # Convert UUID to string
                'offer_type': row.offer_type,
                'propensity_flag': row.propensity_flag,
                'offer_end_date': row.offer_end_date.strftime('%Y-%m-%d') if row.offer_end_date else None,
                'attribution_channel': row.attribution_channel
            })

        df = pd.DataFrame(data)
        current_app.logger.info(f"Generated {len(df)} records for Moengage export.")
        return df
    except Exception as e:
        current_app.logger.error(f"Error generating Moengage data: {e}")
        raise


def get_duplicate_data_for_export():
    """
    Generates a Pandas DataFrame containing data identified as duplicates.
    FR26: The system shall provide a screen for users to download the Duplicate Data File in Excel or CSV format.

    NOTE: The current database schema does not explicitly define a 'deduplication_log' table
    or a clear mechanism to mark 'duplicate' records within the 'customers' table itself,
    as unique constraints are applied to key identifiers.
    For this implementation, we will assume that "duplicate data" refers to records
    that were identified as duplicates during ingestion and potentially logged in
    `DataIngestionLog` with specific error details, or were rejected.
    A more robust solution would involve a dedicated table for deduplication outcomes
    (e.g., `deduplication_history` or `rejected_duplicates`).
    This implementation provides a placeholder based on the `DataIngestionLog` table.
    """
    current_app.logger.info("Retrieving duplicate data for export...")
    try:
        # This query is a placeholder. In a real system, 'duplicate' status would be
        # explicitly tracked, e.g., in a dedicated deduplication log table or by
        # marking records that were merged/rejected.
        # Here, we're looking for ingestion logs that might indicate a duplicate rejection.
        query_results = db.session.query(DataIngestionLog).filter(
            DataIngestionLog.error_details.ilike('%duplicate%') |
            DataIngestionLog.error_details.ilike('%already exists%')
        ).all()

        data = []
        for log in query_results:
            data.append({
                'log_id': str(log.log_id),
                'file_name': log.file_name,
                'upload_timestamp': log.upload_timestamp.isoformat(),
                'status': log.status,
                'error_details': log.error_details,
                'uploaded_by': log.uploaded_by
            })

        df = pd.DataFrame(data)
        current_app.logger.info(f"Retrieved {len(df)} records for duplicate data export.")
        return df
    except Exception as e:
        current_app.logger.error(f"Error retrieving duplicate data: {e}")
        raise


def get_unique_data_for_export():
    """
    Generates a Pandas DataFrame containing unique customer data.
    FR27: The system shall provide a screen for users to download the Unique Data File in Excel or CSV format.
    This typically means all records in the 'customers' table, which represents the unique profiles.
    """
    current_app.logger.info("Retrieving unique customer data for export...")
    try:
        query_results = db.session.query(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan,
            Customer.aadhaar_ref_number,
            Customer.ucid,
            Customer.customer_segment,
            Customer.is_dnd,
            Customer.created_at,
            Customer.updated_at
        ).filter(Customer.is_dnd == False).all() # Assuming unique means non-DND for export purposes

        data = []
        for row in query_results:
            data.append({
                'customer_id': str(row.customer_id),
                'mobile_number': row.mobile_number,
                'pan': row.pan,
                'aadhaar_ref_number': row.aadhaar_ref_number,
                'ucid': row.ucid,
                'customer_segment': row.customer_segment,
                'is_dnd': row.is_dnd,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })

        df = pd.DataFrame(data)
        current_app.logger.info(f"Retrieved {len(df)} records for unique data export.")
        return df
    except Exception as e:
        current_app.logger.error(f"Error retrieving unique data: {e}")
        raise


def get_error_data_for_export():
    """
    Generates a Pandas DataFrame containing data from failed ingestion logs.
    FR28: The system shall provide a screen for users to download the Error Excel file.
    """
    current_app.logger.info("Retrieving error data for export...")
    try:
        query_results = db.session.query(DataIngestionLog).filter(
            DataIngestionLog.status == 'FAILED'
        ).all()

        data = []
        for log in query_results:
            data.append({
                'log_id': str(log.log_id),
                'file_name': log.file_name,
                'upload_timestamp': log.upload_timestamp.isoformat() if log.upload_timestamp else None,
                'status': log.status,
                'error_details': log.error_details,
                'uploaded_by': log.uploaded_by
            })

        df = pd.DataFrame(data)
        current_app.logger.info(f"Retrieved {len(df)} records for error data export.")
        return df
    except Exception as e:
        current_app.logger.error(f"Error retrieving error data: {e}")
        raise


def export_cdp_data_to_edw():
    """
    Task to extract all relevant CDP data and prepare it for transfer to EDW.
    FR23: The system shall pass all data, including campaign data, from LTFS Offer CDP to EDW daily by day end.
    NFR8: The system shall perform daily data transfer from LTFS Offer CDP to EDW by day end.
    This function simulates the extraction and logging of data for EDW.
    The actual transfer mechanism (e.g., S3, SFTP, direct DB link) is external to this function.
    """
    current_app.logger.info("Starting daily CDP data export to EDW...")
    try:
        # Ensure db.session.bind is available for pd.read_sql
        if not db.session.bind:
            current_app.logger.error("Database engine not bound to session. Cannot export to EDW.")
            raise RuntimeError("Database engine not bound for EDW export.")

        # Extract Customers
        customers_df = pd.read_sql(db.session.query(Customer).statement, db.session.bind)
        current_app.logger.info(f"Extracted {len(customers_df)} customer records for EDW.")

        # Extract Offers
        offers_df = pd.read_sql(db.session.query(Offer).statement, db.session.bind)
        current_app.logger.info(f"Extracted {len(offers_df)} offer records for EDW.")

        # Extract Customer Events
        events_df = pd.read_sql(db.session.query(CustomerEvent).statement, db.session.bind)
        current_app.logger.info(f"Extracted {len(events_df)} customer event records for EDW.")

        # Extract Campaigns
        campaigns_df = pd.read_sql(db.session.query(Campaign).statement, db.session.bind)
        current_app.logger.info(f"Extracted {len(campaigns_df)} campaign records for EDW.")

        # In a real scenario, these DataFrames would then be written to a target EDW system.
        # E.g., df.to_csv('s3://edw-bucket/customers.csv'), or pushed via an API.
        # For this simulation, we just log the completion and return summary.

        current_app.logger.info("CDP data extraction for EDW completed. Ready for transfer.")
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
    except Exception as e:
        current_app.logger.error(f"Error during CDP data export to EDW: {e}")
        raise