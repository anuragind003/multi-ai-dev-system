from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

# Assuming these modules exist in the project structure
from app.database import get_db
from app.schemas import (
    LeadCreate,
    EligibilityCheck,
    ApplicationStatusUpdate,
    LOSResponse,
)
from app.services import customer_service, offer_service, event_service

router = APIRouter(prefix="/api/v1/los", tags=["LOS Integration"])


@router.post("/leads", response_model=LOSResponse, status_code=status.HTTP_201_CREATED)
async def receive_lead_data(lead_data: LeadCreate, db: Session = Depends(get_db)):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores in CDP.
    Handles customer deduplication and offer precedence logic.
    (FR11, FR12, FR25-FR32)
    """
    try:
        # 1. Deduplicate or create customer
        # This service call encapsulates FR3, FR4, FR5 (CDP internal deduplication)
        # and potentially FR5 (Customer 360 check, if implemented within customer_service)
        customer_id, is_new_customer = customer_service.get_or_create_customer(
            db,
            mobile_number=lead_data.mobile_number,
            pan_number=lead_data.pan_number,
            aadhaar_ref_number=lead_data.aadhaar_ref_number,
            ucid_number=lead_data.ucid_number,
            previous_loan_app_number=lead_data.previous_loan_app_number,
            customer_attributes={"source_system": lead_data.source_system},
        )

        # 2. Process and create/update offer based on precedence rules
        # This service call encapsulates FR25-FR32 (Offer precedence)
        # and implicitly considers FR15 (preventing modification of started journeys)
        offer_id = offer_service.process_incoming_offer(
            db,
            customer_id=customer_id,
            product_type=lead_data.loan_product,
            offer_details=lead_data.offer_details,
            source_system=lead_data.source_system,
        )

        # 3. Record the lead generation event (FR33)
        event_service.create_campaign_event(
            db,
            customer_id=customer_id,
            offer_id=offer_id,
            event_source="LOS",  # Or specific source like 'Insta', 'E-aggregator'
            event_type="LEAD_GENERATED",
            event_details={
                "loan_product": lead_data.loan_product,
                "source_system": lead_data.source_system,
                "offer_details_snapshot": lead_data.offer_details,
            },
        )

        message = "Lead processed and stored."
        if is_new_customer:
            message += " New customer created."
        else:
            message += " Existing customer updated."

        return LOSResponse(
            status="success", message=message, customer_id=customer_id, offer_id=offer_id
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"Error processing lead data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process lead data: An unexpected error occurred.",
        )


@router.post("/eligibility", response_model=LOSResponse, status_code=status.HTTP_200_OK)
async def update_eligibility_status(
    eligibility_data: EligibilityCheck, db: Session = Depends(get_db)
):
    """
    Receives real-time eligibility check data from LOS/aggregators.
    Updates customer/offer eligibility status and records the event.
    (FR11, FR33)
    """
    try:
        customer = customer_service.get_customer_by_identifiers(
            db,
            mobile_number=eligibility_data.mobile_number,
            pan_number=eligibility_data.pan_number,
            aadhaar_ref_number=eligibility_data.aadhaar_ref_number,
        )
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found for eligibility update.",
            )

        # The eligibility check itself might not directly update an 'offer' record's status
        # but rather inform future offer generation or be recorded as an event.
        # If there's a specific offer to update, offer_service would handle it.
        # For now, we primarily record the event.

        event_service.create_campaign_event(
            db,
            customer_id=customer.customer_id,
            offer_id=None,  # May or may not be tied to a specific offer
            event_source="LOS",
            event_type="ELIGIBILITY_CHECK",
            event_details={
                "product_type": eligibility_data.product_type,
                "eligibility_status": eligibility_data.eligibility_status,
                "eligibility_criteria": eligibility_data.eligibility_criteria_met,
            },
        )

        return LOSResponse(
            status="success",
            message="Eligibility status updated and event recorded.",
            customer_id=customer.customer_id,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error updating eligibility status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update eligibility: An unexpected error occurred.",
        )


@router.post(
    "/application_status", response_model=LOSResponse, status_code=status.HTTP_200_OK
)
async def update_application_status(
    status_data: ApplicationStatusUpdate, db: Session = Depends(get_db)
):
    """
    Receives real-time application journey status updates from LOS.
    Updates offer status (e.g., is_journey_started, loan_application_id)
    and records application stage events.
    (FR11, FR12, FR15, FR33)
    """
    try:
        customer = customer_service.get_customer_by_identifiers(
            db,
            mobile_number=status_data.mobile_number,
            pan_number=status_data.pan_number,
            aadhaar_ref_number=status_data.aadhaar_ref_number,
        )
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found for application status update.",
            )

        # Find the relevant offer and update its journey status
        # This logic should be in offer_service and handle FR15 (prevent modification if journey started)
        updated_offer_id = offer_service.update_offer_journey_status(
            db,
            customer_id=customer.customer_id,
            loan_application_id=status_data.loan_application_id,
            application_stage=status_data.application_stage,
            status_details=status_data.status_details,
        )

        if not updated_offer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active offer found for the given loan application ID or customer, or offer cannot be updated due to journey status.",
            )

        # Record the application stage event (FR33)
        event_service.create_campaign_event(
            db,
            customer_id=customer.customer_id,
            offer_id=updated_offer_id,
            event_source="LOS",
            event_type=f"APP_STAGE_{status_data.application_stage.upper()}",
            event_details=status_data.status_details,
            event_timestamp=status_data.event_timestamp,
        )

        return LOSResponse(
            status="success",
            message=f"Application status updated to {status_data.application_stage}.",
            customer_id=customer.customer_id,
            offer_id=updated_offer_id,
            loan_application_id=status_data.loan_application_id,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error updating application status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update application status: An unexpected error occurred.",
        )