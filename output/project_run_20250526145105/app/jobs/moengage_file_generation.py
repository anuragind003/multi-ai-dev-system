import io
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_moengage_file_content() -> io.StringIO:
    """
    Generates the Moengage-formatted CSV file content from the CDP database.

    Queries customer and offer data, applies business logic for Moengage export,
    and formats it into a CSV string.

    Returns:
        io.StringIO: A file-like object containing the CSV content.
                     Returns an empty StringIO object if no data is found.
    Raises:
        Exception: If there is an error during database interaction or data processing.
    """
    logger.info("Starting Moengage file generation job.")

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    try:
        with SessionLocal() as db:
            # FR34: The system shall avoid DND (Do Not Disturb) customers.
            # FR54: The system shall generate a Moengage format file in .csv format.
            # We select relevant customer and offer data.
            # For campaigning, we typically want 'Active' offers and non-DND customers.
            # FR18: The system shall maintain flags for Offer statuses (Active, Inactive, Expired).
            # Assuming 'Active' offers are the primary ones for Moengage campaigns.
            query = text("""
                SELECT
                    c.customer_id,
                    c.mobile_number,
                    c.pan_number,
                    c.aadhaar_ref_number,
                    c.ucid_number,
                    c.previous_loan_app_number,
                    c.customer_attributes,
                    c.customer_segments,
                    c.propensity_flag,
                    c.dnd_status,
                    o.offer_id,
                    o.offer_type,
                    o.offer_status,
                    o.product_type,
                    o.offer_details,
                    o.offer_start_date,
                    o.offer_end_date,
                    o.is_journey_started,
                    o.loan_application_id
                FROM
                    customers c
                JOIN
                    offers o ON c.customer_id = o.customer_id
                WHERE
                    c.dnd_status = FALSE
                    AND o.offer_status = 'Active' -- Filter for active offers suitable for campaigning
                ORDER BY
                    c.customer_id, o.created_at DESC;
            """)
            result = db.execute(query).fetchall()

            if not result:
                logger.warning("No active customer offers found for Moengage file generation.")
                return io.StringIO("") # Return empty CSV content if no data

            # Convert SQLAlchemy result to a list of dictionaries for pandas DataFrame creation
            columns = result[0]._fields
            data = [dict(zip(columns, row)) for row in result]

            df = pd.DataFrame(data)

            # --- Data Transformation for Moengage format ---
            # Moengage typically expects a flat structure.
            # Handle JSONB fields (customer_attributes, offer_details) by extracting common keys.
            # If a key is not present or the value is not a dictionary, it will default to None.
            df['customer_name'] = df['customer_attributes'].apply(lambda x: x.get('name') if isinstance(x, dict) else None)
            df['customer_email'] = df['customer_attributes'].apply(lambda x: x.get('email') if isinstance(x, dict) else None)
            df['customer_gender'] = df['customer_attributes'].apply(lambda x: x.get('gender') if isinstance(x, dict) else None)

            df['loan_amount'] = df['offer_details'].apply(lambda x: x.get('loan_amount') if isinstance(x, dict) else None)
            df['interest_rate'] = df['offer_details'].apply(lambda x: x.get('interest_rate') if isinstance(x, dict) else None)
            df['tenure'] = df['offer_details'].apply(lambda x: x.get('tenure') if isinstance(x, dict) else None)

            # Handle customer_segments (TEXT[] in DB, convert to comma-separated string)
            df['customer_segments_str'] = df['customer_segments'].apply(lambda x: ','.join(x) if isinstance(x, list) else None)

            # Define the final columns for the Moengage CSV file.
            # These column names should ideally match Moengage's expected import format.
            # 'customer_id' can serve as Moengage's 'USER_ID' or 'CUSTOMER_ID'.
            moengage_output_columns = {
                'customer_id': 'CUSTOMER_ID',
                'mobile_number': 'MOBILE_NUMBER',
                'pan_number': 'PAN_NUMBER',
                'aadhaar_ref_number': 'AADHAAR_REF_NUMBER',
                'ucid_number': 'UCID_NUMBER',
                'previous_loan_app_number': 'PREVIOUS_LOAN_APP_NUMBER',
                'customer_name': 'CUSTOMER_NAME',
                'customer_email': 'CUSTOMER_EMAIL',
                'customer_gender': 'CUSTOMER_GENDER',
                'customer_segments_str': 'CUSTOMER_SEGMENTS',
                'propensity_flag': 'PROPENSITY_FLAG',
                'offer_id': 'OFFER_ID',
                'offer_type': 'OFFER_TYPE',
                'product_type': 'PRODUCT_TYPE',
                'offer_status': 'OFFER_STATUS',
                'loan_amount': 'LOAN_AMOUNT',
                'interest_rate': 'INTEREST_RATE',
                'tenure': 'TENURE',
                'offer_start_date': 'OFFER_START_DATE',
                'offer_end_date': 'OFFER_END_DATE',
                'is_journey_started': 'IS_JOURNEY_STARTED',
                'loan_application_id': 'LOAN_APPLICATION_ID'
            }

            # Select and rename columns for the final Moengage DataFrame
            df_moengage = df.rename(columns=moengage_output_columns)[list(moengage_output_columns.values())]

            # Ensure date columns are formatted correctly if needed (e.g., YYYY-MM-DD)
            for col in ['OFFER_START_DATE', 'OFFER_END_DATE']:
                if col in df_moengage.columns:
                    df_moengage[col] = pd.to_datetime(df_moengage[col]).dt.strftime('%Y-%m-%d')

            # Convert DataFrame to CSV string in an in-memory buffer
            csv_buffer = io.StringIO()
            df_moengage.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0) # Rewind the buffer to the beginning for reading

            logger.info(f"Successfully generated Moengage file with {len(df_moengage)} records.")
            return csv_buffer

    except Exception as e:
        logger.error(f"Error generating Moengage file: {e}", exc_info=True)
        # Re-raise the exception to be handled by the caller (e.g., API endpoint or scheduler)
        raise