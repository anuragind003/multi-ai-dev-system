import csv
import io
from datetime import datetime, date
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

# Assuming db is initialized in app/extensions.py
# Assuming models are defined in app/models/customer.py, app/models/offer.py, app/models/campaign.py
from app.extensions import db
from app.models import Customer, Offer, Campaign # Import necessary models

class CampaignService:
    """
    Service layer for managing campaign-related operations, including
    creating/updating campaign records and generating campaign files.
    """

    def create_or_update_campaign(self, campaign_data: dict) -> Campaign:
        """
        Creates a new campaign record or updates an existing one based on
        campaign_unique_identifier.

        Functional Requirements Addressed:
        - FR33: The system shall maintain all data related to customers and campaigns in CDP.
        - FR34: Campaign data shall include details of all targeted customers and campaign metrics.

        Args:
            campaign_data (dict): A dictionary containing campaign details.
                                  Expected keys: 'campaign_unique_identifier', 'campaign_name',
                                  'campaign_date', 'targeted_customers_count', 'attempted_count',
                                  'successfully_sent_count', 'failed_count', 'success_rate',
                                  'conversion_rate'.

        Returns:
            Campaign: The created or updated Campaign model instance.

        Raises:
            ValueError: If 'campaign_unique_identifier' is missing.
            SQLAlchemyError: If a database operation fails.
            Exception: For any other unexpected errors.
        """
        logger = current_app.logger
        campaign_unique_identifier = campaign_data.get('campaign_unique_identifier')

        if not campaign_unique_identifier:
            logger.error("Attempted to create/update campaign without a unique identifier.")
            raise ValueError("Campaign unique identifier is required.")

        try:
            campaign = Campaign.query.filter_by(campaign_unique_identifier=campaign_unique_identifier).first()

            if campaign:
                # Update existing campaign
                logger.info(f"Updating existing campaign: {campaign_unique_identifier}")
                campaign.campaign_name = campaign_data.get('campaign_name', campaign.campaign_name)
                campaign.campaign_date = campaign_data.get('campaign_date', campaign.campaign_date)
                campaign.targeted_customers_count = campaign_data.get('targeted_customers_count', campaign.targeted_customers_count)
                campaign.attempted_count = campaign_data.get('attempted_count', campaign.attempted_count)
                campaign.successfully_sent_count = campaign_data.get('successfully_sent_count', campaign.successfully_sent_count)
                campaign.failed_count = campaign_data.get('failed_count', campaign.failed_count)
                campaign.success_rate = campaign_data.get('success_rate', campaign.success_rate)
                campaign.conversion_rate = campaign_data.get('conversion_rate', campaign.conversion_rate)
                campaign.updated_at = datetime.now()
            else:
                # Create new campaign
                logger.info(f"Creating new campaign with identifier: {campaign_unique_identifier}")
                campaign = Campaign(
                    campaign_unique_identifier=campaign_unique_identifier,
                    campaign_name=campaign_data.get('campaign_name'),
                    campaign_date=campaign_data.get('campaign_date'),
                    targeted_customers_count=campaign_data.get('targeted_customers_count'),
                    attempted_count=campaign_data.get('attempted_count'),
                    successfully_sent_count=campaign_data.get('successfully_sent_count'),
                    failed_count=campaign_data.get('failed_count'),
                    success_rate=campaign_data.get('success_rate'),
                    conversion_rate=campaign_data.get('conversion_rate')
                )
                db.session.add(campaign)

            db.session.commit()
            logger.info(f"Campaign '{campaign_unique_identifier}' saved successfully.")
            return campaign
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error saving campaign '{campaign_unique_identifier}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred saving campaign '{campaign_unique_identifier}': {e}")
            raise

    def generate_moengage_file(self) -> io.StringIO:
        """
        Generates a CSV file in Moengage format. This file includes data for
        active offers associated with non-DND customers.

        Functional Requirements Addressed:
        - FR25: The system shall provide a screen for users to download the Moengage File in Excel or CSV format.
        - FR39: The system shall provide a front-end utility for LTFS users to download the Moengage format file in .csv format.
        - FR21: Event data shall include SMS sent, SMS delivered, SMS click (from Moengage),
                conversions (from LOS/Moengage), and application stages (login, bureau check,
                offer details, eKYC, Bank details, other details, e-sign) (from LOS),
                avoiding DND Customers. (Implicitly, Moengage file should exclude DND).

        Returns:
            io.StringIO: An in-memory text buffer containing the CSV data.
                         The caller is responsible for reading from this buffer.

        Raises:
            SQLAlchemyError: If a database query fails.
            Exception: For any other unexpected errors during file generation.
        """
        logger = current_app.logger
        output = io.StringIO()
        writer = csv.writer(output)

        # Define CSV headers for Moengage file.
        # These are derived from the database schema and common Moengage requirements.
        # In a real scenario, these would be explicitly defined in the BRD or a template.
        headers = [
            "customer_id", "mobile_number", "pan", "aadhaar_ref_number", "ucid",
            "offer_id", "offer_type", "offer_status", "propensity_flag",
            "offer_start_date", "offer_end_date", "loan_application_number",
            "attribution_channel", "customer_segment"
        ]
        writer.writerow(headers)

        try:
            # Query for active offers for non-DND customers
            # Join Customer and Offer tables to get combined data
            # Filter for offers with 'Active' status and customers who are not marked as DND
            # Order by customer_id and offer_id for consistent output
            records = db.session.query(
                Customer.customer_id,
                Customer.mobile_number,
                Customer.pan,
                Customer.aadhaar_ref_number,
                Customer.ucid,
                Offer.offer_id,
                Offer.offer_type,
                Offer.offer_status,
                Offer.propensity_flag,
                Offer.offer_start_date,
                Offer.offer_end_date,
                Offer.loan_application_number,
                Offer.attribution_channel,
                Customer.customer_segment
            ).join(Offer, Customer.customer_id == Offer.customer_id)\
            .filter(Offer.offer_status == 'Active')\
            .filter(Customer.is_dnd == False)\
            .order_by(Customer.customer_id, Offer.offer_id)\
            .all()

            if not records:
                logger.info("No active offers found for non-DND customers to generate Moengage file.")
                # Still return an empty StringIO object with headers
                output.seek(0)
                return output

            for record in records:
                # Convert SQLAlchemy Row object to a list
                row = list(record)
                # Format date objects to ISO 8601 string for CSV compatibility
                if isinstance(row[9], date): # offer_start_date
                    row[9] = row[9].isoformat()
                if isinstance(row[10], date): # offer_end_date
                    row[10] = row[10].isoformat()
                writer.writerow(row)

            output.seek(0) # Rewind to the beginning of the stream for reading
            logger.info(f"Successfully generated Moengage file with {len(records)} records.")
            return output
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during Moengage file generation: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during Moengage file generation: {e}")
            raise