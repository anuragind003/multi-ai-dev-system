import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign


class ReportService:
    @staticmethod
    def generate_moengage_data():
        """
        Generates data for the Moengage file, excluding DND customers.
        (FR25, FR21)
        Returns a pandas DataFrame with relevant customer and offer details.
        """
        try:
            # Query active offers for non-DND customers
            # Join Customer and Offer tables to get combined data
            # Assuming 'Active' is the status for offers to be sent to Moengage
            # And 'is_dnd' flag in Customer table is respected.
            moengage_records = db.session.query(
                Customer.customer_id,
                Customer.mobile_number,
                Customer.customer_segment,
                Offer.offer_id,
                Offer.offer_type,
                Offer.offer_status,
                Offer.propensity_flag,
                Offer.offer_end_date,
                Offer.loan_application_number
            ).join(Offer, Customer.customer_id == Offer.customer_id)\
            .filter(
                Customer.is_dnd == False,
                Offer.offer_status == 'Active'
            ).all()

            if not moengage_records:
                current_app.logger.info("No active, non-DND customer offers found for Moengage file generation.")
                return pd.DataFrame()  # Return empty DataFrame

            # Convert query results to a list of dictionaries for DataFrame creation
            data = []
            for record in moengage_records:
                data.append({
                    'customer_id': str(record.customer_id),
                    'mobile_number': record.mobile_number,
                    'customer_segment': record.customer_segment,
                    'offer_id': str(record.offer_id),
                    'offer_type': record.offer_type,
                    'offer_status': record.offer_status,
                    'propensity_flag': record.propensity_flag,
                    'offer_end_date': record.offer_end_date.strftime('%Y-%m-%d') if record.offer_end_date else None,
                    'loan_application_number': record.loan_application_number
                    # Add other fields as per Moengage format if known
                })

            df = pd.DataFrame(data)
            current_app.logger.info(f"Generated Moengage data with {len(df)} records.")
            return df

        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error generating Moengage data: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error generating Moengage data: {e}")
            raise

    @staticmethod
    def get_duplicate_data():
        """
        Retrieves data related to duplicate customers or offers. (FR26)
        Given the database schema enforces unique constraints on primary customer identifiers,
        "duplicate data" is interpreted here as customers who have multiple active offers,
        which would be subject to attribution logic (FR20). This report provides context
        for such scenarios. A more robust solution for tracking actual deduplication
        outcomes would require a dedicated deduplication log or audit table.
        """
        try:
            # First, identify customer_ids that have more than one active offer
            customer_ids_with_multiple_offers = db.session.query(
                Customer.customer_id
            ).join(Offer, Customer.customer_id == Offer.customer_id)\
            .filter(Offer.offer_status == 'Active')\
            .group_by(Customer.customer_id)\
            .having(func.count(Offer.offer_id) > 1).all()

            if not customer_ids_with_multiple_offers:
                current_app.logger.info("No customers with multiple active offers found for duplicate data report.")
                return pd.DataFrame()

            # Extract customer_ids from the result
            customer_ids = [c.customer_id for c in customer_ids_with_multiple_offers]

            # Now, retrieve all offers for these identified customers to show the "duplicate" context
            duplicate_records = db.session.query(
                Customer.customer_id,
                Customer.mobile_number,
                Customer.pan,
                Customer.aadhaar_ref_number,
                Customer.ucid,
                Offer.offer_id,
                Offer.offer_type,
                Offer.offer_status,
                Offer.attribution_channel,
                Offer.created_at,
                Offer.offer_end_date
            ).join(Offer, Customer.customer_id == Offer.customer_id)\
            .filter(Customer.customer_id.in_(customer_ids))\
            .order_by(Customer.customer_id, Offer.created_at).all()

            data = []
            for record in duplicate_records:
                data.append({
                    'customer_id': str(record.customer_id),
                    'mobile_number': record.mobile_number,
                    'pan': record.pan,
                    'aadhaar_ref_number': record.aadhaar_ref_number,
                    'ucid': record.ucid,
                    'offer_id': str(record.offer_id),
                    'offer_type': record.offer_type,
                    'offer_status': record.offer_status,
                    'attribution_channel': record.attribution_channel,
                    'offer_created_at': record.created_at.isoformat(),
                    'offer_end_date': record.offer_end_date.strftime('%Y-%m-%d') if record.offer_end_date else None
                })

            df = pd.DataFrame(data)
            current_app.logger.info(f"Generated duplicate data report with {len(df)} records.")
            return df

        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error retrieving duplicate data: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error retrieving duplicate data: {e}")
            raise

    @staticmethod
    def get_unique_data():
        """
        Retrieves data for unique customer profiles. (FR27)
        As the 'customers' table is designed to hold unique profiles after deduplication,
        this function simply retrieves all customer records.
        """
        try:
            unique_customers = db.session.query(
                Customer.customer_id,
                Customer.mobile_number,
                Customer.pan,
                Customer.aadhaar_ref_number,
                Customer.ucid,
                Customer.previous_loan_app_number,
                Customer.customer_segment,
                Customer.is_dnd,
                Customer.created_at,
                Customer.updated_at
            ).all()

            if not unique_customers:
                current_app.logger.info("No unique customer data found.")
                return pd.DataFrame()

            data = []
            for customer in unique_customers:
                data.append({
                    'customer_id': str(customer.customer_id),
                    'mobile_number': customer.mobile_number,
                    'pan': customer.pan,
                    'aadhaar_ref_number': customer.aadhaar_ref_number,
                    'ucid': customer.ucid,
                    'previous_loan_app_number': customer.previous_loan_app_number,
                    'customer_segment': customer.customer_segment,
                    'is_dnd': customer.is_dnd,
                    'created_at': customer.created_at.isoformat(),
                    'updated_at': customer.updated_at.isoformat()
                })

            df = pd.DataFrame(data)
            current_app.logger.info(f"Generated unique data report with {len(df)} records.")
            return df

        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error retrieving unique data: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error retrieving unique data: {e}")
            raise

    @staticmethod
    def get_error_data():
        """
        Retrieves data for failed data ingestion logs. (FR28)
        """
        try:
            error_logs = db.session.query(
                DataIngestionLog.log_id,
                DataIngestionLog.file_name,
                DataIngestionLog.upload_timestamp,
                DataIngestionLog.status,
                DataIngestionLog.error_details,
                DataIngestionLog.uploaded_by
            ).filter(
                or_(
                    DataIngestionLog.status == 'FAILED',
                    DataIngestionLog.status == 'PARTIAL'
                )
            ).order_by(DataIngestionLog.upload_timestamp.desc()).all()

            if not error_logs:
                current_app.logger.info("No error logs found.")
                return pd.DataFrame()

            data = []
            for log in error_logs:
                data.append({
                    'log_id': str(log.log_id),
                    'file_name': log.file_name,
                    'upload_timestamp': log.upload_timestamp.isoformat(),
                    'status': log.status,
                    'error_details': log.error_details,
                    'uploaded_by': log.uploaded_by
                })

            df = pd.DataFrame(data)
            current_app.logger.info(f"Generated error data report with {len(df)} records.")
            return df

        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error retrieving error data: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error retrieving error data: {e}")
            raise

    @staticmethod
    def get_daily_tally_report(report_date_str: str):
        """
        Retrieves daily data tally reports for frontend display. (FR35)
        Args:
            report_date_str (str): Date in 'YYYY-MM-DD' format.
        Returns:
            dict: Daily tally metrics.
        """
        try:
            report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
            # Define start and end of the day for filtering timestamp columns
            start_of_day = datetime.combine(report_date, datetime.min.time())
            end_of_day = datetime.combine(report_date, datetime.max.time())

            # Total customers processed (created or updated on this day)
            total_customers_processed = db.session.query(Customer).filter(
                or_(
                    cast(Customer.created_at, Date) == report_date,
                    cast(Customer.updated_at, Date) == report_date
                )
            ).count()

            # New offers generated on this day
            new_offers_generated = db.session.query(Offer).filter(
                cast(Offer.created_at, Date) == report_date
            ).count()

            # Deduplicated customers: This metric is complex without a specific deduplication
            # audit log. As a proxy, we count customers whose 'updated_at' timestamp falls
            # on this day, excluding those newly created, implying an update to an existing
            # record which could be due to deduplication or enrichment.
            deduplicated_customers_proxy = db.session.query(Customer).filter(
                cast(Customer.updated_at, Date) == report_date,
                cast(Customer.created_at, Date) != report_date  # Exclude newly created, focus on updates
            ).count()

            # Campaign metrics for the day
            campaign_metrics = db.session.query(
                func.sum(Campaign.targeted_customers_count).label('total_targeted'),
                func.sum(Campaign.attempted_count).label('total_attempted'),
                func.sum(Campaign.successfully_sent_count).label('total_sent'),
                func.sum(Campaign.failed_count).label('total_failed')
            ).filter(
                cast(Campaign.campaign_date, Date) == report_date
            ).first()

            # Data ingestion logs summary for the day
            ingestion_summary = db.session.query(
                DataIngestionLog.status,
                func.count(DataIngestionLog.log_id).label('count')
            ).filter(
                cast(DataIngestionLog.upload_timestamp, Date) == report_date
            ).group_by(DataIngestionLog.status).all()

            ingestion_counts = {item.status: item.count for item in ingestion_summary}

            report_data = {
                'date': report_date_str,
                'total_customers_processed': total_customers_processed,
                'new_offers_generated': new_offers_generated,
                'deduplicated_customers_proxy': deduplicated_customers_proxy,
                'campaign_summary': {
                    'targeted': campaign_metrics.total_targeted if campaign_metrics.total_targeted else 0,
                    'attempted': campaign_metrics.total_attempted if campaign_metrics.total_attempted else 0,
                    'sent': campaign_metrics.total_sent if campaign_metrics.total_sent else 0,
                    'failed': campaign_metrics.total_failed if campaign_metrics.total_failed else 0,
                },
                'ingestion_summary': ingestion_counts
            }
            current_app.logger.info(f"Generated daily tally report for {report_date_str}.")
            return report_data

        except ValueError:
            current_app.logger.error(f"Invalid date format for daily tally report: {report_date_str}")
            raise ValueError("Invalid date format. Please use YYYY-MM-DD.")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error retrieving daily tally report for {report_date_str}: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error retrieving daily tally report for {report_date_str}: {e}")
            raise