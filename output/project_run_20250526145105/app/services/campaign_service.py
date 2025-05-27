import io
import json
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.offer import Offer


class CampaignService:
    def __init__(self, db: Session):
        self.db = db

    def generate_moengage_file(self) -> bytes:
        """
        Generates a Moengage-formatted CSV file containing active customer offers,
        excluding DND customers and offers that have expired.

        This method queries the database for relevant customer and offer data,
        applies filtering based on business rules (e.g., active offers, non-DND customers,
        non-expired offers), and formats the data into a CSV suitable for Moengage.

        Returns:
            bytes: The content of the generated CSV file as bytes.
        """
        # Define the columns to be included in the Moengage file.
        # These are derived from the database schema and typical requirements for a CDP
        # pushing data to a marketing automation platform like Moengage.
        # FR54: "The system shall generate a Moengage format file in .csv format."
        # FR34: "The system shall avoid DND (Do Not Disturb) customers."
        # FR51: "The system shall mark offers as expired based on offer end dates for non-journey started customers."
        moengage_columns = [
            "customer_id",
            "mobile_number",
            "pan_number",
            "aadhaar_ref_number",
            "offer_id",
            "product_type",
            "offer_type",
            "offer_status",
            "offer_start_date",
            "offer_end_date",
            "customer_segments",
            "propensity_flag",
            "offer_details",  # This will be a JSON string
        ]

        # Construct the SQLAlchemy query to fetch data.
        # We join the Customer and Offer tables to get a comprehensive view.
        stmt = select(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_ref_number,
            Customer.customer_segments,
            Customer.propensity_flag,
            Offer.offer_id,
            Offer.offer_type,
            Offer.product_type,
            Offer.offer_status,
            Offer.offer_start_date,
            Offer.offer_end_date,
            Offer.offer_details,
        ).join(
            Customer, Customer.customer_id == Offer.customer_id
        ).where(
            # Filter for offers that are currently 'Active' and eligible for campaigning.
            Offer.offer_status == 'Active',
            # Exclude customers who have opted for 'Do Not Disturb'.
            Customer.dnd_status == False,
            # Ensure the offer has not passed its end date.
            Offer.offer_end_date >= date.today()
        )

        # Execute the query and fetch all results.
        result = self.db.execute(stmt).fetchall()

        if not result:
            # If no data is found, return an empty DataFrame with the expected columns
            # to ensure the CSV always has headers.
            df = pd.DataFrame(columns=moengage_columns)
        else:
            # Process the query results into a list of dictionaries,
            # converting complex types (JSONB, TEXT[]) to CSV-friendly strings.
            data = []
            for row in result:
                row_dict = row._asdict()

                # Convert 'offer_details' (JSONB) to a JSON string.
                if row_dict['offer_details'] is not None:
                    row_dict['offer_details'] = json.dumps(row_dict['offer_details'])
                else:
                    row_dict['offer_details'] = "{}"  # Default to empty JSON object string

                # Convert 'customer_segments' (TEXT[]) to a comma-separated string.
                if row_dict['customer_segments'] is not None:
                    row_dict['customer_segments'] = ",".join(row_dict['customer_segments'])
                else:
                    row_dict['customer_segments'] = ""  # Default to empty string

                data.append(row_dict)

            # Create a Pandas DataFrame from the processed data.
            df = pd.DataFrame(data)

            # Reindex the DataFrame to ensure the columns are in the specified order
            # and handle any potential missing columns by filling with empty strings.
            df = df.reindex(columns=moengage_columns, fill_value='')

        # Convert the DataFrame to a CSV string in memory.
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)

        # Encode the CSV string to bytes using UTF-8.
        return csv_buffer.getvalue().encode('utf-8')