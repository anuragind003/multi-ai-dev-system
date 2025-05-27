import csv
import io
from datetime import date

# Assuming DatabaseManager is available from backend.utils.database
# This import path will need to be correctly set up based on the project's
# actual directory structure and how the DatabaseManager is exposed.
# For this service file, we assume it's passed during initialization.


class CampaignService:
    def __init__(self, db_manager):
        """
        Initializes the CampaignService with a database manager.
        :param db_manager: An instance of DatabaseManager for database interactions.
        """
        self.db_manager = db_manager

    def generate_moengage_export_file(self):
        """
        Generates a CSV file in Moengage format containing unique, non-DND customers
        with their most recent active offers.

        The export includes customers who are not marked as 'Do Not Disturb' (DND)
        and have at least one 'Active' offer whose end date has not passed.
        If a customer has multiple active offers, the most recently started one
        (or most recently created if start dates are identical) is selected.

        Returns:
            str: The content of the Moengage CSV file.
        """
        # Query to select non-DND customers and their most recent active offer.
        # A LATERAL JOIN is used to efficiently get the top 1 offer per customer.
        query = """
            SELECT
                c.customer_id,
                c.mobile_number,
                c.pan_number,
                c.segment,
                o.offer_id,
                o.offer_type,
                o.propensity,
                o.start_date,
                o.end_date
            FROM
                customers c
            JOIN LATERAL (
                SELECT
                    offer_id,
                    offer_type,
                    propensity,
                    start_date,
                    end_date,
                    created_at
                FROM
                    offers
                WHERE
                    customer_id = c.customer_id
                    AND offer_status = 'Active'
                    AND end_date >= CURRENT_DATE
                ORDER BY
                    start_date DESC, created_at DESC
                LIMIT 1
            ) o ON TRUE
            WHERE
                c.dnd_flag = FALSE;
        """

        try:
            # Execute the query. Assumes db_manager.execute_query returns a list of dictionaries,
            # where keys are column names.
            results = self.db_manager.execute_query(query)

            # Define CSV headers based on the query's selected columns.
            fieldnames = [
                'customer_id', 'mobile_number', 'pan_number', 'segment',
                'offer_id', 'offer_type', 'propensity', 'start_date', 'end_date'
            ]

            # Use StringIO to build the CSV content in memory.
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)

            writer.writeheader()
            if results:
                for row in results:
                    # Format date objects to ISO format strings (YYYY-MM-DD) for CSV compatibility.
                    # Other data types are written as is.
                    row_data = {k: v.isoformat() if isinstance(v, date) else v for k, v in row.items()}
                    writer.writerow(row_data)

            return output.getvalue()

        except Exception as e:
            # In a production application, use a robust logging framework (e.g., Python's logging module).
            print(f"Error generating Moengage export file: {e}")
            # Re-raise the exception to allow the calling API endpoint to handle it
            # (e.g., return an appropriate HTTP error response).
            raise

    def update_campaign_metrics(self, campaign_unique_id, campaign_name, campaign_date,
                                attempted_count, sent_success_count, failed_count, conversion_rate):
        """
        Updates or inserts campaign metrics into the campaign_metrics table.
        This method uses PostgreSQL's `ON CONFLICT DO UPDATE` clause for an atomic
        upsert operation, ensuring that if a `campaign_unique_id` already exists,
        its metrics are updated; otherwise, a new record is inserted.

        :param campaign_unique_id: A unique identifier for the campaign.
        :param campaign_name: The name of the campaign.
        :param campaign_date: The date the campaign was run.
        :param attempted_count: Total number of attempts for the campaign.
        :param sent_success_count: Number of successfully sent messages/offers.
        :param failed_count: Number of failed attempts.
        :param conversion_rate: The conversion rate for the campaign (e.g., 5.25 for 5.25%).
        """
        query = """
            INSERT INTO campaign_metrics (
                metric_id, campaign_unique_id, campaign_name, campaign_date,
                attempted_count, sent_success_count, failed_count, conversion_rate
            ) VALUES (
                gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (campaign_unique_id) DO UPDATE SET
                campaign_name = EXCLUDED.campaign_name,
                campaign_date = EXCLUDED.campaign_date,
                attempted_count = EXCLUDED.attempted_count,
                sent_success_count = EXCLUDED.sent_success_count,
                failed_count = EXCLUDED.failed_count,
                conversion_rate = EXCLUDED.conversion_rate,
                created_at = CURRENT_TIMESTAMP; -- Using created_at to reflect last update time
        """
        # Note: The `created_at` column in the schema is used here to track the last update time
        # for simplicity, as an `updated_at` column was not explicitly defined in the provided schema.
        # In a full production system, an `updated_at` column with a `DEFAULT now()` and `ON UPDATE now()`
        # trigger would be more appropriate.

        try:
            self.db_manager.execute_insert_update(
                query,
                (campaign_unique_id, campaign_name, campaign_date,
                 attempted_count, sent_success_count, failed_count, conversion_rate)
            )
        except Exception as e:
            print(f"Error updating campaign metrics for campaign '{campaign_unique_id}': {e}")
            raise