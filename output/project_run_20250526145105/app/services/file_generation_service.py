import io
import csv
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

# Assuming models are defined in app.models.models
# Make sure these imports are correct based on your project structure
from app.models.models import Customer, Offer, OfferHistory, CampaignEvent

class FileGenerationService:
    def __init__(self, db: Session):
        """
        Initializes the FileGenerationService with a database session.
        The session is expected to be an asynchronous session if using async DB drivers.
        """
        self.db = db

    async def generate_moengage_file(self) -> io.StringIO:
        """
        Generates a CSV file in Moengage format (FR39, FR54).
        Combines customer and offer data, filtering for active, non-journey-started,
        and non-DND customers/offers suitable for campaigning.
        """
        # Define columns for Moengage file.
        # These are inferred based on typical campaign requirements and available data.
        # Actual columns should be confirmed with Moengage requirements (Ambiguity Q10).
        columns = [
            "customer_id",
            "mobile_number",
            "pan_number",
            "aadhaar_ref_number",
            "offer_id",
            "offer_type",
            "offer_status",
            "product_type",
            "offer_start_date",
            "offer_end_date",
            "is_journey_started",
            "propensity_flag",
            "customer_segments",
            "dnd_status"
            # Additional fields from offer_details JSONB could be extracted here
            # if specific keys are consistently present and required by Moengage.
            # Example: "offer_details_loan_amount", "offer_details_interest_rate"
        ]

        # Query active offers and their associated customer details
        # FR54: "generate a Moengage format file in .csv format."
        # FR34: "The system shall avoid DND (Do Not Disturb) customers."
        # Implied: Only active offers not yet started a journey are relevant for new campaigns.
        stmt = select(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_ref_number,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.product_type,
            Offer.offer_start_date,
            Offer.offer_end_date,
            Offer.is_journey_started,
            Customer.propensity_flag,
            Customer.customer_segments,
            Customer.dnd_status
        ).join(Offer, Customer.customer_id == Offer.customer_id).where(
            Offer.offer_status == "Active",
            Offer.is_journey_started == False,
            Customer.dnd_status == False
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall() # Fetch all results

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(columns) # Write header row

        for row in rows:
            # Convert row to a dictionary to easily access by column name
            row_dict = row._asdict()
            formatted_row = []
            for col in columns:
                value = row_dict.get(col)
                if isinstance(value, list): # For customer_segments (TEXT[])
                    formatted_row.append("|".join(value) if value else "")
                elif isinstance(value, (date, datetime)): # For date and timestamp fields
                    formatted_row.append(value.isoformat())
                elif value is None:
                    formatted_row.append("")
                else:
                    formatted_row.append(str(value))
            writer.writerow(formatted_row)

        output.seek(0) # Rewind to the beginning of the stream
        return output

    async def generate_unique_customers_file(self) -> io.StringIO:
        """
        Generates a CSV file containing unique customer data (FR41).
        This file represents the deduplicated customer profiles in the system.
        """
        columns = [
            "customer_id",
            "mobile_number",
            "pan_number",
            "aadhaar_ref_number",
            "ucid_number",
            "previous_loan_app_number",
            "customer_attributes", # JSONB field
            "customer_segments",
            "propensity_flag",
            "dnd_status",
            "created_at",
            "updated_at"
        ]

        stmt = select(Customer)
        result = await self.db.execute(stmt)
        customers = result.scalars().all() # Fetch all Customer objects

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(columns) # Write header row

        for customer in customers:
            formatted_row = []
            for col in columns:
                value = getattr(customer, col)
                if isinstance(value, list): # For customer_segments
                    formatted_row.append("|".join(value) if value else "")
                elif isinstance(value, dict): # For JSONB fields like customer_attributes
                    formatted_row.append(str(value)) # Convert dict to string representation
                elif isinstance(value, (date, datetime)): # For date and timestamp fields
                    formatted_row.append(value.isoformat())
                elif value is None:
                    formatted_row.append("")
                else:
                    formatted_row.append(str(value))
            writer.writerow(formatted_row)

        output.seek(0)
        return output

    async def generate_duplicate_offers_file(self) -> io.StringIO:
        """
        Generates a CSV file containing offers marked as 'Duplicate' (FR40).
        This helps in reviewing and managing duplicate records as per FR20.
        """
        columns = [
            "offer_id",
            "customer_id",
            "offer_type",
            "offer_status",
            "product_type",
            "offer_start_date",
            "offer_end_date",
            "is_journey_started",
            "loan_application_id",
            "created_at",
            "updated_at"
            # offer_details JSONB could be included if specific keys are needed
        ]

        # Query offers explicitly marked with 'Duplicate' status
        stmt = select(Offer).where(Offer.offer_status == "Duplicate")
        result = await self.db.execute(stmt)
        offers = result.scalars().all() # Fetch all Offer objects

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(columns) # Write header row

        for offer in offers:
            formatted_row = []
            for col in columns:
                value = getattr(offer, col)
                if isinstance(value, (date, datetime)):
                    formatted_row.append(value.isoformat())
                elif value is None:
                    formatted_row.append("")
                else:
                    formatted_row.append(str(value))
            writer.writerow(formatted_row)

        output.seek(0)
        return output

    async def generate_upload_error_file(self, errors: List[Dict[str, Any]]) -> io.StringIO:
        """
        Generates a CSV file for failed data uploads, including an 'Error Desc' column (FR42, FR46).
        `errors` is expected to be a list of dictionaries, where each dict represents a failed row
        and should contain an 'error_desc' key along with the original data that caused the error.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        if not errors:
            # If no errors, return a file with just the expected header
            writer.writerow(["error_desc", "original_data"])
            output.seek(0)
            return output

        # Determine columns from the first error entry, ensuring 'error_desc' is first
        # and then sort other keys for consistent column order.
        all_keys = set()
        for error_entry in errors:
            all_keys.update(error_entry.keys())

        columns = ["error_desc"] + sorted([k for k in all_keys if k != "error_desc"])
        writer.writerow(columns) # Write header row

        for error_entry in errors:
            row_data = []
            for col in columns:
                value = error_entry.get(col, "")
                if isinstance(value, (date, datetime)):
                    row_data.append(value.isoformat())
                elif isinstance(value, dict) or isinstance(value, list):
                    row_data.append(str(value)) # Convert complex types to string
                elif value is None:
                    row_data.append("")
                else:
                    row_data.append(str(value))
            writer.writerow(row_data)

        output.seek(0)
        return output

    async def generate_upload_success_file(self, successes: List[Dict[str, Any]]) -> io.StringIO:
        """
        Generates a CSV file for successful data uploads (FR45).
        `successes` is expected to be a list of dictionaries, where each dict represents
        a successfully processed row, typically including identifiers like customer_id, mobile_number.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        if not successes:
            # If no successes, return a file with a default header
            writer.writerow(["customer_id", "mobile_number", "status"]) # Example default headers
            output.seek(0)
            return output

        # Determine columns from the first success entry for consistent headers
        columns = list(successes[0].keys())
        writer.writerow(columns) # Write header row

        for success_entry in successes:
            row_data = []
            for col in columns:
                value = success_entry.get(col, "")
                if isinstance(value, (date, datetime)):
                    row_data.append(value.isoformat())
                elif isinstance(value, dict) or isinstance(value, list):
                    row_data.append(str(value)) # Convert complex types to string
                elif value is None:
                    row_data.append("")
                else:
                    row_data.append(str(value))
            writer.writerow(row_data)

        output.seek(0)
        return output