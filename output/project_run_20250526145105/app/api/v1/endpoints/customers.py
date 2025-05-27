from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

# Assuming these modules and their contents exist as per project structure
# app.db.session should provide the get_db dependency
from app.db.session import get_db
# app.db.models should define the SQLAlchemy ORM models for Customer, Offer, OfferHistory
from app.db.models import Customer, Offer, OfferHistory
# app.schemas.customer should define the Pydantic schemas for API responses
from app.schemas.customer import CustomerDetailResponse, OfferSummary

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get(
    "/{customer_id}",
    response_model=CustomerDetailResponse,
    summary="Retrieve a single profile view of a customer",
    description="Retrieves a customer's details, current offers, attributes, segments, and journey stages."
)
async def get_customer_details(
    customer_id: UUID,
    db: Session = Depends(get_db)
) -> CustomerDetailResponse:
    """
    Retrieves a single profile view of a customer based on their unique identifier.

    This endpoint fetches comprehensive details about a customer, including their
    personal information, current active offers, a summary of their offer history
    for the past 6 months, their current journey status, and assigned customer segments.

    Args:
        customer_id (UUID): The unique identifier of the customer.
        db (Session): Database session dependency.

    Returns:
        CustomerDetailResponse: A Pydantic model containing the customer's detailed profile.

    Raises:
        HTTPException: If the customer with the given ID is not found (HTTP 404).
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Determine the 'current' offer based on business logic:
    # 1. Prioritize an 'Active' offer where the journey has started (`is_journey_started = True`).
    # 2. If no such offer, pick any 'Active' offer.
    # 3. In case of multiple matching offers, select the most recently updated one.
    current_offer_db = db.query(Offer).filter(
        Offer.customer_id == customer_id,
        Offer.offer_status == 'Active',
        Offer.is_journey_started == True
    ).order_by(desc(Offer.updated_at)).first()

    if not current_offer_db:
        current_offer_db = db.query(Offer).filter(
            Offer.customer_id == customer_id,
            Offer.offer_status == 'Active'
        ).order_by(desc(Offer.updated_at)).first()

    current_offer_response: Optional[OfferSummary] = None
    journey_status: str = "No Active Offer"

    if current_offer_db:
        current_offer_response = OfferSummary(
            offer_id=current_offer_db.offer_id,
            product_type=current_offer_db.product_type,
            offer_status=current_offer_db.offer_status
        )
        if current_offer_db.is_journey_started:
            journey_status = "Journey Started"
        else:
            journey_status = "Offer Active, Journey Not Started"
    else:
        # If no active offer, check for any offer (e.g., expired, duplicate)
        # to infer if a journey was ever started.
        # This provides more context than just "No Active Offer".
        any_offer_db = db.query(Offer).filter(
            Offer.customer_id == customer_id
        ).order_by(desc(Offer.updated_at)).first()
        if any_offer_db and any_offer_db.is_journey_started:
            journey_status = "Journey Previously Started (Offer Inactive/Expired)"

    # Fetch offer history summary for the past 6 months (FR23: "maintain offer history for the past 6 months")
    # Limiting to 10 entries for a summary view, ordered by most recent change.
    offer_history_db = db.query(OfferHistory).filter(
        OfferHistory.customer_id == customer_id,
        OfferHistory.change_timestamp >= func.now() - func.interval('6 months')
    ).order_by(desc(OfferHistory.change_timestamp)).limit(10).all()

    offer_history_summary: List[Dict[str, Any]] = [
        {
            "history_id": str(history.history_id),
            "offer_id": str(history.offer_id),
            "change_timestamp": history.change_timestamp.isoformat(),
            "old_status": history.old_offer_status,
            "new_status": history.new_offer_status,
            "reason": history.change_reason,
            "snapshot_offer_details": history.snapshot_offer_details
        }
        for history in offer_history_db
    ]

    # Customer segments are stored as a TEXT[] array in PostgreSQL,
    # which SQLAlchemy typically maps to a Python list of strings.
    customer_segments = customer.customer_segments if customer.customer_segments else []

    return CustomerDetailResponse(
        customer_id=customer.customer_id,
        mobile_number=customer.mobile_number,
        pan_number=customer.pan_number,
        current_offer=current_offer_response,
        offer_history_summary=offer_history_summary,
        journey_status=journey_status,
        segments=customer_segments
    )