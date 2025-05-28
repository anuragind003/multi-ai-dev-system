import logging
import io
import base64
import uuid
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Import the initialized Celery app from the app.tasks package's __init__.py
# This assumes that app/tasks/__init__.py contains:
# from celery import Celery
# celery_app = Celery('cdp_tasks')
from app.tasks import celery_app

# Import Flask application context and database extension
# Assuming 'db' is an SQLAlchemy instance initialized in app/extensions.py
# and 'create_app' is available in app/__init__.py to push application context for tasks.
from app import create_app
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign

logger = logging.getLogger(__name__)

@celery_app.task
def process_daily_offermart_feed():
    """
    FR7: The system shall receive Offer data and Customer data from Offermart daily by creating a staging area (Offer DB to CDP DB).
    NFR5: The system shall handle daily data pushes from Offermart to CDP.
    This task simulates the daily ingestion of data from Offermart.
    It would involve reading data, validating, deduplicating, and storing in CDP.
    """
    logger.info("Starting daily Offermart data ingestion task...")
    app = create_app()
    with app.app_context():
        try:
            # --- Placeholder for actual data ingestion logic ---
            # 1. Connect to Offermart DB or read daily files (e.g., from a shared drive/S3).
            #    Example: df = pd.read_sql("SELECT * FROM offermart_daily_feed", db.engine)
            #    For now, simulate an empty dataframe.
            df = pd.DataFrame() # Replace with actual data loading

            if df.empty:
                logger.info("No new data found in Offermart feed for today.")
                return {"status": "completed", "message": "No new Offermart data to process."}

            # 2. FR1: Perform basic column-level validation.
            #    Example: validated_df = validate_offermart_data(df)
            #    (This function would be defined in a service layer, e.g., app/services/data_validation.py)
            validated_df = df # Placeholder for actual validation

            # 3. Process data for Customers and Offers.
            #    Iterate through validated_df and insert/update Customer and Offer models.
            #    This is where FR3, FR4, FR5 (deduplication) and FR20 (attribution) would be applied.
            new_customers_count = 0
            updated_offers_count = 0
            # for index, row in validated_df.iterrows():
            #     # Example: Deduplication logic (FR3, FR4, FR5)
            #     customer = Customer.query.filter_by(mobile_number=row['mobile_number']).first()
            #     if not customer:
            #         customer = Customer(mobile_number=row['mobile_number'], pan=row.get('pan'), ...)
            #         db.session.add(customer)
            #         db.session.flush() # To get customer_id
            #         new_customers_count += 1
            #     # Example: Offer creation/update (FR6, FR20)
            #     offer = Offer.query.filter_by(customer_id=customer.customer_id, offer_id=row['offer_id']).first()
            #     if offer:
            #         # Update existing offer (FR6)
            #         offer.offer_status = row['new_status']
            #         updated_offers_count += 1
            #     else:
            #         # Create new offer
            #         offer = Offer(customer_id=customer.customer_id, offer_type=row['offer_type'], ...)
            #         db.session.add(offer)
            # db.session.commit()

            logger.info(f"Simulating Offermart data processing: {len(validated_df)} records processed.")
            logger.info(f"New customers: {new_customers_count}, Updated offers: {updated_offers_count}.")

            # Log success
            log_entry = DataIngestionLog(
                file_name="offermart_daily_feed",
                upload_timestamp=datetime.utcnow(),
                status="SUCCESS",
                uploaded_by="system_batch",
                error_details=f"Processed {len(validated_df)} records."
            )
            db.session.add(log_entry)
            db.session.commit()
            logger.info("Daily Offermart feed processed successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing daily Offermart feed: {e}", exc_info=True)
            log_entry = DataIngestionLog(
                file_name="offermart_daily_feed",
                upload_timestamp=datetime.utcnow(),
                status="FAILED",
                error_details=str(e),
                uploaded_by="system_batch"
            )
            db.session.add(log_entry)
            db.session.commit()
            raise # Re-raise to mark task as failed in Celery

    return {"status": "completed", "message": "Daily Offermart feed processing finished."}

@celery_app.task
def generate_and_push_reverse_feed_to_offermart():
    """
    FR8: The system shall push a daily reverse feed to Offermart, including Offer data updates from E-aggregators, on an hourly/daily basis.
    NFR6: The system shall handle hourly/daily reverse feeds from CDP to Offermart.
    This task generates and pushes updated offer data back to Offermart.
    """
    logger.info("Starting reverse feed generation and push to Offermart task...")
    app = create_app()
    with app.app_context():
        try:
            # --- Placeholder for actual reverse feed logic ---
            # 1. Query CDP DB for relevant offer data updates (e.g., offers updated by E-aggregators).
            #    Example: updated_offers = Offer.query.filter(Offer.updated_at > (datetime.utcnow() - timedelta(hours=24))).all()
            #    For now, simulate an empty list.
            updated_offers = [] # Replace with actual query

            if not updated_offers:
                logger.info("No updated offers found for reverse feed to Offermart.")
                return {"status": "completed", "message": "No reverse feed data to push."}

            # 2. Format data as required by Offermart.
            #    Example: df_reverse_feed = pd.DataFrame([offer.to_dict() for offer in updated_offers])
            # 3. Push data to Offermart (e.g., via API, SFTP, or direct DB update).
            logger.info(f"Simulating reverse feed generation and push to Offermart for {len(updated_offers)} records.")
            # push_to_offermart_api(df_reverse_feed) # This function would be in a service layer

            logger.info("Reverse feed to Offermart generated and pushed successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating/pushing reverse feed to Offermart: {e}", exc_info=True)
            raise

    return {"status": "completed", "message": "Reverse feed to Offermart finished."}

@celery_app.task
def push_cdp_data_to_edw():
    """
    FR23: The system shall pass all data, including campaign data, from LTFS Offer CDP to EDW daily by day end.
    NFR8: The system shall perform daily data transfer from LTFS Offer CDP to EDW by day end.
    This task extracts data from CDP and pushes it to the Enterprise Data Warehouse (EDW).
    """
    logger.info("Starting daily CDP data push to EDW task...")
    app = create_app()
    with app.app_context():
        try:
            # --- Placeholder for actual EDW data push logic ---
            # 1. Query CDP DB for all relevant data (customers, offers, events, campaigns).
            #    Example: customers_df = pd.read_sql("SELECT * FROM customers", db.engine)
            #    offers_df = pd.read_sql("SELECT * FROM offers", db.engine)
            #    events_df = pd.read_sql("SELECT * FROM customer_events", db.engine)
            #    campaigns_df = pd.read_sql("SELECT * FROM campaigns", db.engine)
            #    For now, simulate data extraction.
            total_records_to_push = Customer.query.count() + Offer.query.count() + \
                                    CustomerEvent.query.count() + Campaign.query.count()

            if total_records_to_push == 0:
                logger.info("No data found in CDP to push to EDW.")
                return {"status": "completed", "message": "No CDP data to push to EDW."}

            # 2. Transform data for EDW schema (if necessary).
            # 3. Push data to EDW (e.g., via a dedicated ETL process, direct DB insert, or file transfer).
            logger.info(f"Simulating CDP data extraction and push to EDW for approx. {total_records_to_push} records.")
            # push_to_edw(customers_df, offers_df, events_df, campaigns_df) # This function would be in a service layer

            logger.info("CDP data pushed to EDW successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error pushing CDP data to EDW: {e}", exc_info=True)
            raise

    return {"status": "completed", "message": "CDP data push to EDW finished."}

@celery_app.task
def enforce_data_retention_policies():
    """
    NFR3: The system shall retain offer history data for 06 months. (FR18)
    NFR4: The system shall retain all data within LTFS Offer CDP for a period of 3 months before deletion. (FR24)
    This task cleans up old data based on defined retention policies.
    """
    logger.info("Starting data retention policy enforcement task...")
    app = create_app()
    with app.app_context():
        try:
            # Calculate retention thresholds
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            three_months_ago = datetime.utcnow() - timedelta(days=90)

            # FR18, NFR3: Delete offer history older than 6 months (e.g., expired offers)
            # Assuming 'Expired' offers are part of history to be purged.
            deleted_offers_count = Offer.query.filter(
                Offer.offer_status == 'Expired',
                Offer.updated_at < six_months_ago
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_offers_count} expired offers older than 6 months.")

            # FR24, NFR4: Delete other data older than 3 months
            # Customer events
            deleted_events_count = CustomerEvent.query.filter(
                CustomerEvent.event_timestamp < three_months_ago
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_events_count} customer events older than 3 months.")

            # Data ingestion logs
            deleted_logs_count = DataIngestionLog.query.filter(
                DataIngestionLog.upload_timestamp < three_months_ago
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_logs_count} data ingestion logs older than 3 months.")

            # Note: Deleting from 'customers' or 'campaigns' tables directly based on 3 months
            # might be too aggressive unless specific business rules define it.
            # The BRD says "all data in LTFS Offer CDP for previous 3 months before deletion"
            # which needs clarification (Ambiguity 2). For now, focusing on historical/event data.

            db.session.commit()
            logger.info("Data retention policies enforced successfully.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error enforcing data retention policies: {e}", exc_info=True)
            raise

    return {"status": "completed", "message": "Data retention policies enforcement finished."}

@celery_app.task
def update_offer_expiry_status():
    """
    FR13: The system shall prevent modification of customer offers with started loan application journeys until the loan application is either expired or rejected.
    FR37: The system shall implement expiry logic where offers for non-journey started customers depend on offer end dates, allowing replenishment of expired offers.
    FR38: The system shall mark offers as expired within the offers data if the Loan Application Number (LAN) validity post loan application journey start date is over.
    This task updates the status of offers to 'Expired' based on business rules.
    """
    logger.info("Starting offer expiry status update task...")
    app = create_app()
    with app.app_context():
        try:
            active_offers = Offer.query.filter_by(offer_status='Active').all()
            updated_count = 0
            for offer in active_offers:
                # FR38: Logic for offers with started loan application journeys
                if offer.loan_application_number:
                    # This would typically involve checking the status of the loan application
                    # from CustomerEvent (application stages) or an external LOS system.
                    # For simulation, assume a function `is_loan_app_expired_or_rejected`
                    # if is_loan_app_expired_or_rejected(offer.loan_application_number):
                    #     offer.offer_status = 'Expired'
                    #     updated_count += 1
                    pass # Placeholder for actual LAN validity check
                # FR37: Logic for non-journey started offers based on offer_end_date
                elif offer.offer_end_date and offer.offer_end_date < datetime.utcnow().date():
                    offer.offer_status = 'Expired'
                    updated_count += 1
                    logger.debug(f"Offer {offer.offer_id} expired based on end date.")

            db.session.commit()
            logger.info(f"Offer expiry statuses updated successfully. {updated_count} offers marked as expired.")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating offer expiry statuses: {e}", exc_info=True)
            raise

    return {"status": "completed", "message": "Offer expiry status update finished."}

@celery_app.task
def process_uploaded_customer_file(log_id: str, file_content_base64: str, file_type: str, uploaded_by: str):
    """
    Asynchronous task to process uploaded customer details files from the Admin Portal.
    FR29: The Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.
    FR30: The Admin Portal shall generate a lead for customers in the system upon successful file upload.
    FR31: The Admin Portal shall generate a success file upon successful upload of all data.
    FR32: The Admin Portal shall generate an error file with an 'Error Desc' column for failed uploads.
    """
    logger.info(f"Starting processing of uploaded file for log_id: {log_id}, file_type: {file_type} by {uploaded_by}")
    app = create_app()
    with app.app_context():
        log_entry = DataIngestionLog.query.get(uuid.UUID(log_id))
        if not log_entry:
            logger.error(f"DataIngestionLog entry with ID {log_id} not found.")
            return {"status": "failed", "message": f"Log entry {log_id} not found."}

        try:
            file_content_bytes = base64.b64decode(file_content_base64)
            # Assuming the file is CSV. Could add logic for Excel based on file_type.
            df = pd.read_csv(io.BytesIO(file_content_bytes))

            success_records = []
            error_records = []

            for index, row in df.iterrows():
                row_dict = row.to_dict()
                try:
                    # FR1: Basic column-level validation (example: mobile_number)
                    mobile_number = str(row_dict.get('mobile_number')).strip()
                    if not mobile_number or not mobile_number.isdigit() or len(mobile_number) < 10:
                        raise ValueError("Invalid or missing mobile number.")

                    pan = str(row_dict.get('pan')).strip() if pd.notna(row_dict.get('pan')) else None
                    aadhaar_ref_number = str(row_dict.get('aadhaar_ref_number')).strip() if pd.notna(row_dict.get('aadhaar_ref_number')) else None
                    ucid = str(row_dict.get('ucid')).strip() if pd.notna(row_dict.get('ucid')) else None
                    previous_loan_app_number = str(row_dict.get('previous_loan_app_number')).strip() if pd.notna(row_dict.get('previous_loan_app_number')) else None

                    # FR3, FR4, FR5: Deduplication logic
                    # Prioritize matching based on mobile, PAN, Aadhaar, UCID, previous loan application number
                    customer = Customer.query.filter(
                        (Customer.mobile_number == mobile_number) |
                        (Customer.pan == pan) |
                        (Customer.aadhaar_ref_number == aadhaar_ref_number) |
                        (Customer.ucid == ucid) |
                        (Customer.previous_loan_app_number == previous_loan_app_number)
                    ).first()

                    if not customer:
                        customer = Customer(
                            mobile_number=mobile_number,
                            pan=pan,
                            aadhaar_ref_number=aadhaar_ref_number,
                            ucid=ucid,
                            previous_loan_app_number=previous_loan_app_number,
                            customer_segment='C1' # Default, or derive from file_type/data
                        )
                        db.session.add(customer)
                        db.session.flush() # To get customer_id before commit

                    # FR30: Generate a lead (represented by creating an offer)
                    # Assuming basic offer details from the uploaded file or defaults
                    offer_type = 'Fresh' # Or map from file_type (e.g., 'Prospect' -> 'Fresh')
                    offer_status = 'Active'
                    offer_start_date = datetime.utcnow().date()
                    offer_end_date = offer_start_date + timedelta(days=30) # Default 30 days validity

                    offer = Offer(
                        customer_id=customer.customer_id,
                        offer_type=offer_type,
                        offer_status=offer_status,
                        offer_start_date=offer_start_date,
                        offer_end_date=offer_end_date,
                        # Add other offer details from row_dict if available
                    )
                    db.session.add(offer)
                    db.session.commit() # Commit each record to ensure atomicity per row

                    success_records.append(row_dict)
                    logger.debug(f"Successfully processed record for mobile: {mobile_number}")

                except (ValueError, IntegrityError, SQLAlchemyError) as e:
                    db.session.rollback() # Rollback current transaction for this row
                    error_row = row_dict
                    error_row['Error Desc'] = str(e)
                    error_records.append(error_row)
                    logger.warning(f"Error processing row (index {index}): {e} - Data: {row_dict}")
                except Exception as e:
                    db.session.rollback()
                    error_row = row_dict
                    error_row['Error Desc'] = f"Unexpected error: {e}"
                    error_records.append(error_row)
                    logger.error(f"Unexpected error processing row (index {index}): {e} - Data: {row_dict}", exc_info=True)

            # Update DataIngestionLog status based on processing results
            if not error_records:
                log_entry.status = 'SUCCESS'
                log_entry.error_details = None
                logger.info(f"File {log_id} processed successfully with no errors.")
            elif len(success_records) > 0:
                log_entry.status = 'PARTIAL'
                log_entry.error_details = f"{len(error_records)} errors encountered. {len(success_records)} records processed successfully."
                logger.warning(f"File {log_id} processed with partial success.")
            else:
                log_entry.status = 'FAILED'
                log_entry.error_details = f"All records failed. Total records: {len(df)}. Errors: {len(error_records)}."
                logger.error(f"File {log_id} processing failed completely.")
            db.session.commit()

            # FR31, FR32: Generate success/error files (in a real system, these would be saved to storage)
            if success_records:
                success_df = pd.DataFrame(success_records)
                # Example: save to a temporary location or cloud storage
                # success_file_path = f"/tmp/uploads/{log_id}_success.csv"
                # success_df.to_csv(success_file_path, index=False)
                logger.info(f"Generated success data for {log_id}: {len(success_records)} records.")
            if error_records:
                error_df = pd.DataFrame(error_records)
                # Example: save to a temporary location or cloud storage
                # error_file_path = f"/tmp/uploads/{log_id}_error.csv"
                # error_df.to_csv(error_file_path, index=False)
                logger.info(f"Generated error data for {log_id}: {len(error_records)} records.")

        except Exception as e:
            db.session.rollback()
            log_entry.status = 'FAILED'
            log_entry.error_details = f"Critical file processing error: {e}"
            db.session.commit()
            logger.error(f"Critical error during file processing for log_id {log_id}: {e}", exc_info=True)
            raise # Re-raise to mark task as failed in Celery

    return {"status": "completed", "message": f"File processing for {log_id} finished."}