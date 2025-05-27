from typing import List, Optional
from uuid import UUID, uuid4
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.customer import CustomerCreate, CustomerProfileView, CustomerUpdate
from app.schemas.offer import OfferCreate, OfferUpdate, OfferInDB, OfferHistoryCreate
from app.schemas.lead import LeadCreate, LeadResponse
from app.crud import customer as customer_crud
from app.crud import offer as offer_crud
from app.models.customer import Customer as CustomerModel
from app.models.offer import Offer as OfferModel
from app.models.offer_history import OfferHistory as OfferHistoryModel

router = APIRouter()

@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_200_OK)
async def process_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores it in CDP.
    Applies deduplication and offer precedence logic.
    """
    # FR3: Deduplicate customers based on Mobile number, Pan number, Aadhaar reference number, UCID number, or previous loan application number.
    existing_customer = customer_crud.get_customer_by_identifiers(
        db,
        mobile_number=lead_in.mobile_number,
        pan_number=lead_in.pan_number,
        aadhaar_ref_number=lead_in.aadhaar_ref_number,
        ucid_number=lead_in.ucid_number,
        previous_loan_app_number=lead_in.previous_loan_app_number
    )

    customer_id: UUID
    message: str = "Lead processed and stored."

    if existing_customer:
        customer_id = existing_customer.customer_id
        message = "Lead processed for existing customer."

        # FR15, FR21, FR26, FR27, FR28: Check for existing active offer and journey status
        active_offer = offer_crud.get_active_offer_for_customer(db, customer_id)

        if active_offer:
            if active_offer.is_journey_started:
                # FR15: Prevent modification if journey started.
                # FR21: If an Enrich offer's journey has started, it shall not flow into CDP.
                # FR26, FR27, FR28: Direct to existing offer if journey started.
                return LeadResponse(
                    status="success",
                    message=f"Customer has an active offer with journey started. Directed to existing offer {active_offer.offer_id}.",
                    customer_id=customer_id
                )
            else:
                # FR20, FR25: If no journey started, new offer prevails. Mark old as Duplicate/Expired.
                # This is a simplified precedence logic for MVP.
                # Real implementation would involve complex FR29-FR32 rules.
                offer_crud.update_offer(
                    db,
                    db_offer=active_offer,
                    offer_update=OfferUpdate(offer_status="Duplicate", updated_at=datetime.now())
                )
                offer_crud.create_offer_history_entry(
                    db,
                    OfferHistoryCreate(
                        offer_id=active_offer.offer_id,
                        customer_id=customer_id,
                        old_offer_status=active_offer.offer_status,
                        new_offer_status="Duplicate",
                        change_reason="New lead received, old offer superseded.",
                        snapshot_offer_details=active_offer.offer_details
                    )
                )
                message += " Existing active offer marked as Duplicate."

        # Update existing customer attributes if new data is provided (e.g., segments, propensity)
        customer_update_data = {}
        if lead_in.customer_attributes:
            customer_update_data["customer_attributes"] = lead_in.customer_attributes
        if lead_in.customer_segments:
            customer_update_data["customer_segments"] = lead_in.customer_segments
        if lead_in.propensity_flag:
            customer_update_data["propensity_flag"] = lead_in.propensity_flag
        if customer_update_data:
            customer_crud.update_customer(db, existing_customer, CustomerUpdate(**customer_update_data))

    else:
        # Create new customer
        new_customer_id = uuid4()
        customer_create_data = CustomerCreate(
            customer_id=new_customer_id,
            mobile_number=lead_in.mobile_number,
            pan_number=lead_in.pan_number,
            aadhaar_ref_number=lead_in.aadhaar_ref_number,
            ucid_number=lead_in.ucid_number,
            previous_loan_app_number=lead_in.previous_loan_app_number,
            customer_attributes=lead_in.customer_attributes,
            customer_segments=lead_in.customer_segments,
            propensity_flag=lead_in.propensity_flag,
            dnd_status=False # FR34: DND status should be handled, default to False for new leads
        )
        customer_crud.create_customer(db, customer_create_data)
        customer_id = new_customer_id

    # Create new offer for the customer
    new_offer_id = uuid4()
    offer_create_data = OfferCreate(
        offer_id=new_offer_id,
        customer_id=customer_id,
        offer_type="Fresh", # Assuming new leads are 'Fresh' offers
        offer_status="Active",
        product_type=lead_in.loan_product,
        offer_details=lead_in.offer_details,
        offer_start_date=date.today(),
        offer_end_date=date.today() + timedelta(days=30), # Example: offer valid for 30 days
        is_journey_started=False,
        loan_application_id=None
    )
    offer_crud.create_offer(db, offer_create_data)

    return LeadResponse(status="success", message=message, customer_id=customer_id)

@router.get("/{customer_id}", response_model=CustomerProfileView, status_code=status.HTTP_200_OK)
async def get_customer_profile(customer_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieves a single profile view of a customer, including their current offers,
    attributes, segments, and journey stages.
    """
    customer = customer_crud.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found."
        )

    current_offer_db = offer_crud.get_active_offer_for_customer(db, customer_id)
    current_offer_schema: Optional[OfferInDB] = None
    if current_offer_db:
        current_offer_schema = OfferInDB.model_validate(current_offer_db)

    # FR23: Maintain offer history for the past 6 months for reference purposes.
    six_months_ago = datetime.now() - timedelta(days=6 * 30) # Approximate 6 months
    offer_history_db = offer_crud.get_offers_history_for_customer(db, customer_id, from_date=six_months_ago)
    offer_history_summary = [OfferHistoryCreate.model_validate(h) for h in offer_history_db]

    # Determine journey status based on the active offer
    journey_status = "No Active Offer"
    if current_offer_db:
        if current_offer_db.is_journey_started:
            journey_status = f"Journey Started (LAN: {current_offer_db.loan_application_id})"
        else:
            journey_status = "Offer Active (Journey Not Started)"

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
        current_offer=current_offer_schema,
        offer_history_summary=offer_history_summary,
        journey_status=journey_status
    )