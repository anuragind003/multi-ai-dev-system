from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timedelta

# Assuming these are defined in app/database.py and app/models/
from app.database import get_db
from app.models.customer import Customer
from app.models.offer import Offer, OfferHistory

# Pydantic models for request and response bodies
# In a real project, these would typically be in app/schemas/lead.py
from pydantic import BaseModel, Field

class LeadCreate(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=20, description="Customer's mobile number")
    pan_number: Optional[str] = Field(None, min_length=10, max_length=10, description="Customer's PAN number")
    aadhaar_ref_number: Optional[str] = Field(None, min_length=12, max_length=12, description="Customer's Aadhaar reference number")
    ucid_number: Optional[str] = Field(None, max_length=50, description="Customer's UCID number")
    previous_loan_application_number: Optional[str] = Field(None, max_length=50, description="Customer's previous loan application number")
    loan_product: str = Field(..., description="Type of loan product, e.g., Insta, E-aggregator, Prospect, TW Loyalty, Top-up, Employee Loan")
    offer_details: Dict[str, Any] = Field(..., description="Flexible JSON for offer specific data, e.g., loan amount, interest rate")

class LeadResponse(BaseModel):
    status: str = Field(..., description="Status of the lead processing (success/failure)")
    message: str = Field(..., description="Detailed message about the processing outcome")
    customer_id: Optional[UUID] = Field(None, description="UUID of the customer, new or existing")
    offer_id: Optional[UUID] = Field(None, description="UUID of the newly created offer, if any")
    redirect_to_existing_offer: Optional[bool] = Field(False, description="True if customer is directed to an existing offer instead of creating a new one")
    existing_offer_id: Optional[UUID] = Field(None, description="UUID of the existing offer if redirection occurs")
    existing_product_type: Optional[str] = Field(None, description="Product type of the existing offer if redirection occurs")


router = APIRouter()

async def handle_offer_precedence(
    db: Session,
    customer: Customer,
    incoming_loan_product: str,
    incoming_offer_details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applies FR25-FR32 logic to determine if a new offer should be created
    or if the customer should be directed to an existing offer.
    Returns a dictionary with processing outcome.
    """
    response_data = {
        "create_new_offer": False,
        "message": "Lead processed successfully.",
        "redirect_to_existing_offer": False,
        "existing_offer_id": None,
        "existing_product_type": None
    }

    existing_active_offers = db.query(Offer).filter(
        Offer.customer_id == customer.customer_id,
        Offer.offer_status == 'Active'
    ).all()

    # Case A: Incoming is 'Insta' or 'E-aggregator' (Real-time API)
    if incoming_loan_product in ['Insta', 'E-aggregator']:
        # Flag to track if any FR25 condition was met and offers were expired
        fr25_applied = False
        for offer in existing_active_offers:
            # FR25: If existing is pre-approved (prospect or E-aggregator) with no journey started
            if offer.product_type in ['Preapproved', 'Prospect', 'E-aggregator'] and not offer.is_journey_started:
                offer.offer_status = 'Expired' # As per FR25: "uploaded pre-approved offer will expire."
                offer.updated_at = datetime.now()
                db.add(OfferHistory(
                    offer_id=offer.offer_id,
                    customer_id=customer.customer_id,
                    old_offer_status='Active',
                    new_offer_status='Expired',
                    change_reason=f"Superseded by new {incoming_loan_product} offer (FR25)",
                    snapshot_offer_details=offer.offer_details
                ))
                fr25_applied = True
                # Continue loop to expire all relevant offers, then proceed.
                continue

            # FR26, FR27, FR28: If existing has journey started OR is a "stronger" offer type
            # This implies that if a journey has started, or if it's already a real-time/specific loan offer,
            # the new real-time lead should direct to the existing one.
            if offer.is_journey_started or \
               offer.product_type in ['Insta', 'E-aggregator', 'TW Loyalty', 'Top-up', 'Employee Loan']:
                response_data["redirect_to_existing_offer"] = True
                response_data["existing_offer_id"] = offer.offer_id
                response_data["existing_product_type"] = offer.product_type
                response_data["message"] = f"Customer directed to existing {offer.product_type} offer (FR26/FR27/FR28)."
                response_data["create_new_offer"] = False # Do not create new offer
                return response_data # Return immediately as redirection takes precedence

        # If no blocking/superseding offers found, and no redirection, create new Insta/E-aggregator offer
        # This path is taken if FR25 was applied (offers expired) or no relevant active offers existed.
        if not response_data["redirect_to_existing_offer"]:
            response_data["create_new_offer"] = True
            if fr25_applied:
                response_data["message"] = f"Existing pre-approved offers expired, new {incoming_loan_product} offer created."
        return response_data

    # Case B: Incoming is 'Prospect', 'TW Loyalty', 'Top-up', or 'Employee Loan' (Admin Portal Upload type)
    elif incoming_loan_product in ['Prospect', 'TW Loyalty', 'Top-up', 'Employee Loan']:
        # FR29-FR32: These rules state that if *any* of these specific offer types
        # ('TW Loyalty', 'Topup', 'Employee loan', 'Preapproved', 'Prospect')
        # *already exist* as active offers, then a *new* offer of 'Prospect', 'TW Loyalty', 'Top-up',
        # or 'Employee Loan' *cannot* be uploaded.
        blocking_offer_types = ['TW Loyalty', 'Top-up', 'Employee Loan', 'Preapproved', 'Prospect', 'E-aggregator'] # E-aggregator added based on FR29 context
        for offer in existing_active_offers:
            if offer.product_type in blocking_offer_types:
                response_data["create_new_offer"] = False
                response_data["message"] = f"New {incoming_loan_product} offer cannot be uploaded due to existing active {offer.product_type} offer (FR29-FR32)."
                response_data["redirect_to_existing_offer"] = True # Indicate redirection to existing
                response_data["existing_offer_id"] = offer.offer_id
                response_data["existing_product_type"] = offer.product_type
                return response_data # Return immediately as new offer is blocked

        # If no blocking offers found, create new offer
        response_data["create_new_offer"] = True
        return response_data

    # Default: If product type is not covered by specific rules, or no active offers
    response_data["create_new_offer"] = True
    return response_data


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_200_OK)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores in CDP.
    Applies deduplication and offer precedence logic.
    """
    customer_id: Optional[UUID] = None
    offer_id: Optional[UUID] = None
    message: str = "Lead processed successfully."
    redirect_to_existing_offer: bool = False
    existing_offer_id: Optional[UUID] = None
    existing_product_type: Optional[str] = None

    # 1. Deduplication / Customer Lookup (FR3)
    # Prioritize lookup by unique identifiers
    existing_customer = None
    if lead.mobile_number:
        existing_customer = db.query(Customer).filter(Customer.mobile_number == lead.mobile_number).first()
    if not existing_customer and lead.pan_number:
        existing_customer = db.query(Customer).filter(Customer.pan_number == lead.pan_number).first()
    if not existing_customer and lead.aadhaar_ref_number:
        existing_customer = db.query(Customer).filter(Customer.aadhaar_ref_number == lead.aadhaar_ref_number).first()
    if not existing_customer and lead.ucid_number:
        existing_customer = db.query(Customer).filter(Customer.ucid_number == lead.ucid_number).first()
    if not existing_customer and lead.previous_loan_application_number:
        existing_customer = db.query(Customer).filter(Customer.previous_loan_app_number == lead.previous_loan_application_number).first()

    if existing_customer:
        customer_id = existing_customer.customer_id
        # FR34: Check DND status
        if existing_customer.dnd_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer is on Do Not Disturb (DND) list. Lead cannot be processed."
            )
        # Update existing customer details if new info is provided (e.g., PAN/Aadhaar might be new)
        if not existing_customer.pan_number and lead.pan_number:
            existing_customer.pan_number = lead.pan_number
        if not existing_customer.aadhaar_ref_number and lead.aadhaar_ref_number:
            existing_customer.aadhaar_ref_number = lead.aadhaar_ref_number
        if not existing_customer.ucid_number and lead.ucid_number:
            existing_customer.ucid_number = lead.ucid_number
        if not existing_customer.previous_loan_app_number and lead.previous_loan_application_number:
            existing_customer.previous_loan_app_number = lead.previous_loan_application_number
        existing_customer.updated_at = datetime.now()
    else:
        # Create new customer (FR2)
        customer_id = uuid4()
        new_customer = Customer(
            customer_id=customer_id,
            mobile_number=lead.mobile_number,
            pan_number=lead.pan_number,
            aadhaar_ref_number=lead.aadhaar_ref_number,
            ucid_number=lead.ucid_number,
            previous_loan_app_number=lead.previous_loan_application_number,
            customer_attributes={}, # Initialize empty, can be enriched later (FR17)
            customer_segments=[], # Initialize empty, can be enriched later (FR17, FR24)
            propensity_flag=None, # Will be received from Offermart (FR22)
            dnd_status=False, # New customer, assume not DND by default
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_customer)
        existing_customer = new_customer # Use this for offer precedence logic

    # 2. Offer Precedence Logic (FR25-FR32)
    # This logic is complex and depends on existing offers and incoming offer type.
    # It determines if a new offer should be created or if the customer is redirected.
    precedence_outcome = await handle_offer_precedence(
        db,
        existing_customer,
        lead.loan_product,
        lead.offer_details
    )

    redirect_to_existing_offer = precedence_outcome["redirect_to_existing_offer"]
    existing_offer_id = precedence_outcome["existing_offer_id"]
    existing_product_type = precedence_outcome["existing_product_type"]
    message = precedence_outcome["message"]

    if precedence_outcome["create_new_offer"]:
        # Determine offer validity (e.g., 30 days from now)
        offer_start_date = datetime.now().date()
        # Default validity period, can be overridden by offer_details if present
        offer_end_date = offer_start_date + timedelta(days=30)

        new_offer = Offer(
            offer_id=uuid4(),
            customer_id=customer_id,
            offer_type='Fresh', # Most new leads are 'Fresh' offers (FR19)
            offer_status='Active', # (FR18)
            product_type=lead.loan_product,
            offer_details=lead.offer_details,
            offer_start_date=offer_start_date,
            offer_end_date=offer_end_date,
            is_journey_started=False, # New lead, journey not started yet
            loan_application_id=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_offer)
        offer_id = new_offer.offer_id

    try:
        db.commit()
        # Refresh objects to ensure they reflect the committed state, especially if new
        db.refresh(existing_customer)
        if offer_id:
            db.refresh(new_offer)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process lead due to database error: {str(e)}"
        )

    return LeadResponse(
        status="success",
        message=message,
        customer_id=customer_id,
        offer_id=offer_id,
        redirect_to_existing_offer=redirect_to_existing_offer,
        existing_offer_id=existing_offer_id,
        existing_product_type=existing_product_type
    )