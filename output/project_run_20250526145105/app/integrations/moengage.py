import io
import json
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.customer import Customer
from app.models.offer import Offer

router = APIRouter()


@router.get(
    "/moengage_file",
    summary="Generate Moengage-formatted campaign file",
    description="Generates and provides the latest Moengage-formatted campaign file in CSV format for download. Includes active offers for non-DND customers.",
    response_class=StreamingResponse,
)
async def get_moengage_campaign_file(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Generates a CSV file containing customer and offer data formatted for Moengage campaigns.
    Filters for active offers and non-DND customers (FR34).
    Includes data for active offers (FR18).
    The generated file is in .csv format (FR54).
    """
    try:
        # Query active offers and their associated non-DND customers
        # Join Customer and Offer tables to get comprehensive data
        stmt = select(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_ref_number,
            Customer.ucid_number,
            Customer.previous_loan_app_number,
            Customer.customer_attributes,
            Customer.customer_segments,
            Customer.propensity_flag,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.product_type,
            Offer.offer_details,
            Offer.offer_start_date,
            Offer.offer_end_date,
        ).join(Offer, Customer.customer_id == Offer.customer_id).where(
            Offer.offer_status == "Active",  # Only include active offers for campaigning
            Customer.dnd_status == False  # FR34: Avoid DND (Do Not Disturb) customers
        )

        result = await session.execute(stmt)
        records = result.all()

        if not records:
            raise HTTPException(status_code=404, detail="No active campaign data found to generate Moengage file.")

        # Prepare data for Pandas DataFrame
        data = []
        for record in records:
            # Convert JSONB fields to JSON strings for CSV compatibility
            customer_attributes_json = json.dumps(record.customer_attributes) if record.customer_attributes else "{}"
            offer_details_json = json.dumps(record.offer_details) if record.offer_details else "{}"
            # Convert array of text (customer_segments) to a comma-separated string
            customer_segments_str = ", ".join(record.customer_segments) if record.customer_segments else ""

            data.append({
                "customer_id": str(record.customer_id),
                "mobile_number": record.mobile_number,
                "pan_number": record.pan_number,
                "aadhaar_ref_number": record.aadhaar_ref_number,
                "ucid_number": record.ucid_number,
                "previous_loan_app_number": record.previous_loan_app_number,
                "offer_id": str(record.offer_id),
                "product_type": record.product_type,
                "offer_type": record.offer_type,
                "offer_status": record.offer_status,
                "offer_start_date": record.offer_start_date.isoformat() if record.offer_start_date else None,
                "offer_end_date": record.offer_end_date.isoformat() if record.offer_end_date else None,
                "customer_segments": customer_segments_str,
                "propensity_flag": record.propensity_flag,
                "offer_details_json": offer_details_json,
                "customer_attributes_json": customer_attributes_json,
            })

        # Create DataFrame from the prepared data
        df = pd.DataFrame(data)

        # Generate CSV in memory using StringIO
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)  # Move to the beginning of the stream to read its content

        # Define filename with current timestamp for uniqueness
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"moengage_campaign_data_{current_time}.csv"

        # Return the CSV file as a StreamingResponse
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException as e:
        # Re-raise FastAPI HTTPExceptions directly
        raise e
    except Exception as e:
        # Catch any other unexpected errors and return a 500 Internal Server Error
        print(f"Error generating Moengage file: {e}")  # Log the error for debugging
        raise HTTPException(status_code=500, detail=f"Failed to generate Moengage file: {e}")