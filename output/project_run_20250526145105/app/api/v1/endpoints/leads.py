from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID

# Assuming these modules exist and provide the necessary functionality
# For database session management
from app.db.session import get_db, AsyncSession
# For business logic related to leads, customers, and offers
from app.services.lead_service import LeadService, LeadProcessingResult, LeadProcessingError

router = APIRouter()

class LeadCreateRequest(BaseModel):
    """
    Request model for real-time lead generation API.
    Corresponds to data received from external aggregators/Insta.
    """
    mobile_number: str = Field(..., description="Customer's mobile number")
    pan_number: Optional[str] = Field(None, description="Customer's PAN number")
    aadhaar_ref_number: Optional[str] = Field(None, description="Customer's Aadhaar reference number")
    ucid_number: Optional[str] = Field(None, description="Customer's UCID number")
    previous_loan_app_number: Optional[str] = Field(None, description="Customer's previous loan application number")
    loan_product: str = Field(..., description="Type of loan product (e.g., 'Insta', 'E-aggregator', 'Preapproved')")
    offer_details: Dict[str, Any] = Field(..., description="JSON object containing specific offer details")
    source_channel: Optional[str] = Field(None, description="Source channel of the lead (e.g., 'Insta', 'E-aggregator_X')")
    campaign_id: Optional[str] = Field(None, description="Campaign identifier associated with the lead")

class LeadCreateResponse(BaseModel):
    """
    Response model for successful lead creation or processing.
    """
    status: str = Field(..., description="Status of the lead processing (e.g., 'created', 'processed_existing', 'existing_offer_prevails')")
    message: str = Field(..., description="Descriptive message about the processing outcome")
    customer_id: UUID = Field(..., description="Unique identifier of the customer")
    offer_id: Optional[UUID] = Field(None, description="Unique identifier of the offer created or updated")

@router.post("/", response_model=LeadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives real-time lead generation data from external aggregators/Insta.
    Processes the lead by performing deduplication, applying offer precedence rules,
    and storing/updating customer and offer data in the CDP.

    - **Deduplication (FR3, FR4, FR5, FR6):** Identifies existing customers based on provided identifiers.
    - **DND Check (FR34):** Prevents processing for customers on the Do Not Disturb list.
    - **Offer Precedence (FR25-FR32):** Applies business rules to determine if a new offer
      should prevail over an existing one, or vice-versa.
    - **Journey Status Check (FR15, FR21):** Prevents modification of offers if a loan
      application journey has already started.
    - **Offer Status & Type Management (FR18, FR19, FR20):** Updates offer statuses
      (e.g., 'Active', 'Expired', 'Duplicate') and types ('Fresh', 'Enrich', etc.).
    """
    lead_service = LeadService(db)

    try:
        result: LeadProcessingResult = await lead_service.process_lead(
            mobile_number=lead_data.mobile_number,
            pan_number=lead_data.pan_number,
            aadhaar_ref_number=lead_data.aadhaar_ref_number,
            ucid_number=lead_data.ucid_number,
            previous_loan_app_number=lead_data.previous_loan_app_number,
            loan_product=lead_data.loan_product,
            offer_details=lead_data.offer_details,
            source_channel=lead_data.source_channel,
            campaign_id=lead_data.campaign_id
        )

        # Determine appropriate HTTP status code based on the processing outcome
        http_status_code = status.HTTP_201_CREATED # Default for new creation
        if result.status == "processed_existing" or result.status == "existing_offer_prevails":
            http_status_code = status.HTTP_200_OK # OK if an existing record was updated/processed

        return LeadCreateResponse(
            status=result.status,
            message=result.message,
            customer_id=result.customer_id,
            offer_id=result.offer_id
        )

    except LeadProcessingError as e:
        # Map custom service errors to appropriate HTTP exceptions
        if e.code == "DND_CUSTOMER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Lead processing failed: {e.message}"
            )
        elif e.code == "JOURNEY_STARTED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, # Conflict if existing journey prevents new offer
                detail=f"Lead processing failed: {e.message}"
            )
        elif e.code == "INVALID_INPUT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lead processing failed: {e.message}"
            )
        else:
            # Catch any other specific LeadProcessingError codes not explicitly handled
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected business rule error occurred during lead processing: {e.message}"
            )
    except Exception as e:
        # Catch any other unexpected errors during the process
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unhandled server error occurred: {str(e)}"
        )