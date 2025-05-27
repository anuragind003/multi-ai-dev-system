from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta, timezone
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Customer, Offer, CampaignEvent

# Pydantic model for the Daily Tally Report response
class DailyTallyReport(BaseModel):
    """
    Represents the structure of the daily data tally report.
    """
    report_date: date = Field(..., example="2023-10-27", description="Date for which the report is generated.")
    total_customers: int = Field(..., example=15000, description="Total number of customers in the system.")
    active_offers: int = Field(..., example=7500, description="Total number of offers currently marked as 'Active'.")
    new_leads_today: int = Field(..., example=150, description="Number of new customer leads generated today.")
    conversions_today: int = Field(..., example=25, description="Number of successful conversions recorded today.")

# Initialize the FastAPI router for reports endpoints
# The prefix "/reports" will make all endpoints in this file accessible under /api/v1/reports/...
router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

@router.get(
    "/daily_tally",
    response_model=DailyTallyReport,
    summary="Get Daily Data Tally Report",
    description="Provides daily summary reports for data tally, including counts of unique customers, active offers, new leads, and conversions for the current day."
)
async def get_daily_tally_report(db: Session = Depends(get_db)):
    """
    Retrieves a daily summary report of key operational metrics.

    This endpoint calculates and returns:
    - `total_customers`: The total count of all customers in the CDP.
    - `active_offers`: The total count of offers currently marked with an 'Active' status.
    - `new_leads_today`: The number of new customer records created within the current day.
    - `conversions_today`: The number of 'CONVERSION' events recorded within the current day.

    The report date is automatically set to the current server date.
    """
    today_date = date.today()

    # Define the start and end of the current day in UTC for accurate timestamp filtering.
    # It's crucial to handle timezones consistently, assuming database timestamps
    # are stored in UTC or are timezone-aware and handled correctly by SQLAlchemy.
    start_of_today_utc = datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc)
    end_of_today_utc = datetime.combine(today_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    try:
        # Query total number of customers from the Customer model
        total_customers = db.query(Customer).count()

        # Query total number of active offers from the Offer model
        active_offers = db.query(Offer).filter(Offer.offer_status == "Active").count()

        # Query new leads today: Customers whose 'created_at' timestamp falls within the current day
        new_leads_today = db.query(Customer).filter(
            Customer.created_at >= start_of_today_utc,
            Customer.created_at < end_of_today_utc
        ).count()

        # Query conversions today: Campaign events of type 'CONVERSION' whose 'event_timestamp'
        # falls within the current day
        conversions_today = db.query(CampaignEvent).filter(
            CampaignEvent.event_type == "CONVERSION",
            CampaignEvent.event_timestamp >= start_of_today_utc,
            CampaignEvent.event_timestamp < end_of_today_utc
        ).count()

        # Return the aggregated data using the Pydantic response model
        return DailyTallyReport(
            report_date=today_date,
            total_customers=total_customers,
            active_offers=active_offers,
            new_leads_today=new_leads_today,
            conversions_today=conversions_today,
        )
    except Exception as e:
        # In a production environment, detailed error logging should be implemented here
        # (e.g., using a dedicated logging library like `logging`).
        print(f"Error fetching daily tally report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the daily tally report. Please try again later."
        )