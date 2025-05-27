import csv
import io
from datetime import datetime

# Assuming these models are defined in src/models/customer.py and src/models/offer.py
# and are accessible via direct import or through a __init__.py in src/models
from src.models.customer import Customer
from src.models.offer import Offer
# Assuming db_session is defined in src/database.py and provides a context manager
from src.database import db_session

class MoengageExportService:
    """
    Service class responsible for generating customer and offer data
    in a CSV format suitable for Moengage campaign uploads.
    """

    def __init__(self):
        """
        Initializes the MoengageExportService.
        """
        pass

    def generate_moengage_csv(self) -> io.StringIO:
        """
        Queries the database for active customer and offer data,
        filters out DND customers, and formats the data into a CSV string
        stream for Moengage.

        Returns:
            io.StringIO: An in-memory text buffer containing the CSV data.
                         The stream's cursor is reset to the beginning.
        Raises:
            Exception: If a database error occurs during data retrieval.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Define CSV headers. These are common fields expected by campaign management systems
        # like Moengage for customer segmentation and personalized campaigns.
        # Based on FR31, FR44, FR23 and general Moengage requirements.
        headers = [
            "customer_id",
            "mobile_number",
            "segment",
            "offer_id",
            "offer_type",
            "offer_status",
            "propensity",
            "offer_start_date",
            "offer_end_date",
            "channel"
        ]
        writer.writerow(headers)

        try:
            # Use the db_session context manager to ensure proper session handling
            # (e.g., commit on success, rollback on error, close session).
            with db_session() as session:
                # Query customers and their associated active offers.
                # FR23: Exclude customers marked with dnd_flag = True.
                # Only include offers with 'Active' status for campaigning.
                query_results = session.query(
                    Customer.customer_id,
                    Customer.mobile_number,
                    Customer.segment,
                    Offer.offer_id,
                    Offer.offer_type,
                    Offer.offer_status,
                    Offer.propensity,
                    Offer.start_date,
                    Offer.end_date,
                    Offer.channel
                ).join(Offer, Customer.customer_id == Offer.customer_id) \
                .filter(Customer.dnd_flag == False) \
                .filter(Offer.offer_status == 'Active') \
                .all()

                for row in query_results:
                    # Format date fields to 'YYYY-MM-DD' string format.
                    # Handle cases where dates might be None by providing an empty string.
                    offer_start_date_str = row.start_date.strftime('%Y-%m-%d') if row.start_date else ''
                    offer_end_date_str = row.end_date.strftime('%Y-%m-%d') if row.end_date else ''

                    writer.writerow([
                        row.customer_id,
                        row.mobile_number,
                        row.segment,
                        row.offer_id,
                        row.offer_type,
                        row.offer_status,
                        row.propensity,
                        offer_start_date_str,
                        offer_end_date_str,
                        row.channel
                    ])

            # Rewind the stream to the beginning so that its content can be read from the start.
            output.seek(0)
            return output
        except Exception as e:
            # In a production environment, use a robust logging framework (e.g., Python's logging module)
            # instead of print. This allows for better error tracking and alerting.
            print(f"Error generating Moengage CSV: {e}")
            # Re-raise the exception to allow the calling Flask route to handle it
            # (e.g., return a 500 Internal Server Error response).
            raise