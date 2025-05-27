import datetime
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.dependencies import get_db
from app.models.customer import Customer
from app.models.offer import Offer, OfferHistory
from app.models.campaign_event import CampaignEvent

from pydantic import BaseModel, Field
from datetime import date, datetime

# Pydantic models for API responses, defined here for self-containment as per instructions.
# In a larger project, these might reside in a dedicated `app/schemas/report.py` file.

class OfferSummary(BaseModel):
    offer_id: uuid.UUID
    product_type: str
    offer_status: str
    offer_start_date: Optional[date] = None
    offer_end_date: Optional[date] = None
    is_journey_started: bool

class OfferHistoryEntry(BaseModel):
    history_id: uuid.UUID
    offer_id: uuid.UUID
    change_timestamp: datetime
    old_offer_status: Optional[str] = None
    new_offer_status: Optional[str] = None
    change_reason: Optional[str] = None

class CustomerProfileView(BaseModel):
    customer_id: uuid.UUID
    mobile_number: Optional[str] = None
    pan_number: Optional[str] = None
    aadhaar_ref_number: Optional[str] = None
    ucid_number: Optional[str] = None
    previous_loan_app_number: Optional[str] = None
    customer_attributes: Optional[dict] = None
    customer_segments: Optional[List[str]] = None
    propensity_flag: Optional[str] = None
    dnd_status: bool
    current_offer: Optional[OfferSummary] = None
    offer_history_summary: List[OfferHistoryEntry] = []
    journey_status: str # Derived status

class DailyTallyReport(BaseModel):
    report_date: date
    total_customers: int
    active_offers: int
    new_leads_today: int
    conversions_today: int


router = APIRouter()


@router.get("/daily_tally", response_model=DailyTallyReport)
async def get_daily_tally_report(db: Session = Depends(get_db)):
    """
    Provides daily summary reports for data tally, including counts of unique customers,
    offers, and processed records.
    """
    today = datetime.now().date()

    # Total customers
    total_customers = db.query(Customer).count()

    # Active offers
    active_offers = db.query(Offer).filter(Offer.offer_status == "Active").count()

    # New leads today (assuming 'LEAD_GENERATED' or 'API_LEAD' event types for new leads)
    new_leads_today = db.query(CampaignEvent).filter(
        cast(CampaignEvent.event_timestamp, Date) == today,
        CampaignEvent.event_type.in_(['LEAD_GENERATED', 'API_LEAD']) # Example event types for lead generation
    ).count()

    # Conversions today (assuming 'CONVERSION' event type from LOS)
    conversions_today = db.query(CampaignEvent).filter(
        cast(CampaignEvent.event_timestamp, Date) == today,
        CampaignEvent.event_type == 'CONVERSION'
    ).count()

    return DailyTallyReport(
        report_date=today,
        total_customers=total_customers,
        active_offers=active_offers,
        new_leads_today=new_leads_today,
        conversions_today=conversions_today
    )


@router.get("/customers/{customer_id}", response_model=CustomerProfileView)
async def get_customer_profile_view(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieves a single profile view of a customer, including their current offers,
    attributes, segments, and journey stages.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )

    # Get current active offer (most recent active offer if multiple exist, though ideally one active)
    current_offer_db = db.query(Offer).filter(
        Offer.customer_id == customer_id,
        Offer.offer_status == "Active"
    ).order_by(Offer.created_at.desc()).first()

    current_offer_summary: Optional[OfferSummary] = None
    journey_status = "No Journey Started"

    if current_offer_db:
        current_offer_summary = OfferSummary(
            offer_id=current_offer_db.offer_id,
            product_type=current_offer_db.product_type,
            offer_status=current_offer_db.offer_status,
            offer_start_date=current_offer_db.offer_start_date,
            offer_end_date=current_offer_db.offer_end_date,
            is_journey_started=current_offer_db.is_journey_started
        )
        if current_offer_db.is_journey_started:
            journey_status = "Journey Started"
            # Further refinement for journey_status could involve querying CampaignEvents
            # for the latest LOS stage (e.g., 'LOGIN', 'BUREAU_CHECK', 'EKYC', 'E-SIGN').
            # For this implementation, we simplify to "Journey Started" if any offer has begun.

    # Get offer history for the past 6 months (FR23)
    six_months_ago = datetime.now() - datetime.timedelta(days=6 * 30) # Approximate 6 months
    offer_history_db = db.query(OfferHistory).filter(
        OfferHistory.customer_id == customer_id,
        OfferHistory.change_timestamp >= six_months_ago
    ).order_by(OfferHistory.change_timestamp.desc()).all()

    offer_history_summary = [
        OfferHistoryEntry(
            history_id=entry.history_id,
            offer_id=entry.offer_id,
            change_timestamp=entry.change_timestamp,
            old_offer_status=entry.old_offer_status,
            new_offer_status=entry.new_offer_status,
            change_reason=entry.change_reason
        ) for entry in offer_history_db
    ]

    return CustomerProfileView(
        customer_id=customer.customer_id,
        mobile_number=customer.mobile_number,
        pan_number=customer.pan_number,
        aadhaar_ref_number=customer.aadhaar_ref_number,
        ucid_number=customer.ucid_number,
        previous_loan_app_number=customer.previous_loan_app_number,
        customer_attributes=customer.customer_attributes,
        customer_segments=customer.customer_segments,
        propensity_flag=customer.propensity_flag,
        dnd_status=customer.dnd_status,
        current_offer=current_offer_summary,
        offer_history_summary=offer_history_summary,
        journey_status=journey_status
    )