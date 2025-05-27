from typing import List, Optional
from uuid import UUID, uuid4
import io
import csv
from datetime import date, datetime, timedelta
import json # Required for handling JSONB fields

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

# Assuming these are defined in app/database.py and app/models.py
from app.database import get_db
from app.models import Customer, Offer, OfferHistory, CampaignEvent

# Assuming these are defined in app/schemas.py
# Minimal Pydantic schemas for request/response bodies and enums
from pydantic import BaseModel, Field
from enum import Enum

class OfferStatusEnum(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    EXPIRED = "Expired"
    DUPLICATE = "Duplicate"
    JOURNEY_STARTED = "Journey Started" # Custom status for FR15, FR21

class OfferTypeEnum(str, Enum):
    FRESH = "Fresh"
    ENRICH = "Enrich"
    NEW_OLD = "New-old"
    NEW_NEW = "New-new"

class ProductTypeEnum(str, Enum):
    LOYALTY = "Loyalty"
    PREAPPROVED = "Preapproved"
    E_AGGREGATOR = "E-aggregator"
    INSTA = "Insta"
    TOP_UP = "Top-up"
    EMPLOYEE_LOAN = "Employee Loan"
    PROSPECT = "Prospect" # Added based on FR43

class LeadCreate(BaseModel):
    mobile_number: str = Field(..., max_length=20)
    pan_number: Optional[str] = Field(None, max_length=10)
    aadhaar_ref_number: Optional[str] = Field(None, max_length=12)
    loan_product: ProductTypeEnum
    offer_details: dict = Field(default_factory=dict) # Flexible storage for offer specific data
    # Additional fields that might come from Insta/E-aggregator
    ucid_number: Optional[str] = Field(None, max_length=50)
    previous_loan_app_number: Optional[str] = Field(None, max_length=50)
    # For simplicity, assuming offer_start_date and offer_end_date are part of offer_details or derived
    offer_start_date: Optional[date] = None
    offer_end_date: Optional[date] = None

class CustomerOfferUploadResponse(BaseModel):
    status: str
    message: str
    job_id: UUID

class OfferResponse(BaseModel):
    offer_id: UUID
    product_type: ProductTypeEnum
    offer_status: OfferStatusEnum
    offer_details: dict
    offer_start_date: Optional[date]
    offer_end_date: Optional[date]
    is_journey_started: bool
    loan_application_id: Optional[str]

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility

class CustomerProfileResponse(BaseModel):
    customer_id: UUID
    mobile_number: Optional[str]
    pan_number: Optional[str]
    aadhaar_ref_number: Optional[str]
    ucid_number: Optional[str]
    previous_loan_app_number: Optional[str]
    customer_attributes: Optional[dict]
    customer_segments: Optional[List[str]]
    propensity_flag: Optional[str]
    dnd_status: bool
    current_offer: Optional[OfferResponse]
    offer_history_summary: List[dict] # Simplified for now, could be OfferHistoryResponse
    journey_status: Optional[str] # Derived from current_offer.is_journey_started or campaign_events

    class Config:
        from_attributes = True

router = APIRouter(prefix="/api/v1", tags=["Offers"])

# --- Helper/Service functions (simplified for direct inclusion in endpoint file) ---
# In a real project, these would be in a separate 'services' module.

def _deduplicate_and_process_offer(db: Session, customer_data: dict, offer_data: dict) -> Customer:
    """
    Handles deduplication and applies offer precedence rules.
    This is a highly simplified placeholder for complex FR2-FR6, FR15, FR16, FR18-FR21, FR25-FR32.
    """
    mobile = customer_data.get("mobile_number")
    pan = customer_data.get("pan_number")
    aadhaar = customer_data.get("aadhaar_ref_number")
    ucid = customer_data.get("ucid_number")
    prev_loan_app_num = customer_data.get("previous_loan_app_number")
    product_type = offer_data.get("product_type")

    # FR3: Deduplicate based on Mobile, Pan, Aadhaar, UCID, or previous loan app number
    existing_customer = db.query(Customer).filter(
        or_(
            Customer.mobile_number == mobile if mobile else False,
            Customer.pan_number == pan if pan else False,
            Customer.aadhaar_ref_number == aadhaar if aadhaar else False,
            Customer.ucid_number == ucid if ucid else False,
            Customer.previous_loan_app_number == prev_loan_app_num if prev_loan_app_num else False,
        )
    ).first()

    if existing_customer:
        # FR34: Avoid DND customers
        if existing_customer.dnd_status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer is on DND list.")

        # FR15, FR21: Prevent modification if journey started
        active_offers_with_journey = db.query(Offer).filter(
            Offer.customer_id == existing_customer.customer_id,
            Offer.offer_status == OfferStatusEnum.ACTIVE,
            Offer.is_journey_started == True
        ).first()

        if active_offers_with_journey:
            # FR15: If journey started, new offer cannot modify existing.
            # FR26, FR27, FR28: Direct to existing offer if journey started.
            # FR21: If an Enrich offer's journey has started, it shall not flow into CDP.
            # For simplicity, we'll just prevent new offer creation if an active journey exists.
            # More complex logic would involve checking offer types and specific precedence rules.
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Customer has an active loan application journey (Offer ID: {active_offers_with_journey.offer_id}). New offer cannot be processed.")

        # FR25-FR32: Complex offer precedence rules. This is a simplified example.
        # This logic needs to be robustly implemented based on specific product types.
        # Example: If new offer is 'Enrich' and old offer's journey not started (FR20)
        # For now, we'll just mark old active offers as 'Inactive' or 'Duplicate' if a new one comes.
        # A more detailed implementation would involve a matrix of product types and their precedence.
        current_active_offer = db.query(Offer).filter(
            Offer.customer_id == existing_customer.customer_id,
            Offer.offer_status == OfferStatusEnum.ACTIVE
        ).first()

        if current_active_offer:
            # FR20: If an Enrich offer's journey has not started, it shall flow to CDP,
            # and the previous offer will be moved to Duplicate.
            # This is a simplified rule. Real logic needs to check new offer type and old offer type.
            # For now, if a new offer comes, the old active one becomes 'Duplicate'.
            current_active_offer.offer_status = OfferStatusEnum.DUPLICATE
            db.add(current_active_offer)
            db.flush() # Ensure ID is available for history

            # Record history for the old offer
            history_entry = OfferHistory(
                offer_id=current_active_offer.offer_id,
                customer_id=existing_customer.customer_id,
                old_offer_status=OfferStatusEnum.ACTIVE,
                new_offer_status=OfferStatusEnum.DUPLICATE,
                change_reason="New offer received, old offer marked as duplicate/inactive",
                snapshot_offer_details=current_active_offer.offer_details
            )
            db.add(history_entry)

        # Update existing customer details if new data is more complete/recent
        existing_customer.mobile_number = mobile or existing_customer.mobile_number
        existing_customer.pan_number = pan or existing_customer.pan_number
        existing_customer.aadhaar_ref_number = aadhaar or existing_customer.aadhaar_ref_number
        existing_customer.ucid_number = ucid or existing_customer.ucid_number
        existing_customer.previous_loan_app_number = prev_loan_app_num or existing_customer.previous_loan_app_number
        existing_customer.updated_at = datetime.now()
        db.add(existing_customer)
        db.flush() # Ensure customer_id is available

        customer = existing_customer
    else:
        # Create new customer
        customer = Customer(
            customer_id=uuid4(),
            mobile_number=mobile,
            pan_number=pan,
            aadhaar_ref_number=aadhaar,
            ucid_number=ucid,
            previous_loan_app_number=prev_loan_app_num,
            customer_attributes={}, # Placeholder
            customer_segments=[], # Placeholder
            propensity_flag=None, # Placeholder
            dnd_status=False # Default, to be updated from Offermart/other sources
        )
        db.add(customer)
        db.flush() # Ensure customer_id is available

    # Create new offer for the customer
    new_offer = Offer(
        offer_id=uuid4(),
        customer_id=customer.customer_id,
        offer_type=offer_data.get("offer_type", OfferTypeEnum.FRESH), # Default to Fresh if not specified
        offer_status=OfferStatusEnum.ACTIVE, # New offers are active by default
        product_type=product_type,
        offer_details=offer_data.get("offer_details", {}),
        offer_start_date=offer_data.get("offer_start_date", date.today()),
        offer_end_date=offer_data.get("offer_end_date", date.today() + timedelta(days=30)), # Default 30 days
        is_journey_started=False
    )
    db.add(new_offer)
    db.flush() # Ensure offer_id is available for history

    # Record history for the new offer
    history_entry = OfferHistory(
        offer_id=new_offer.offer_id,
        customer_id=customer.customer_id,
        old_offer_status=None,
        new_offer_status=OfferStatusEnum.ACTIVE,
        change_reason="New offer created",
        snapshot_offer_details=new_offer.offer_details
    )
    db.add(history_entry)

    db.commit()
    db.refresh(customer)
    db.refresh(new_offer)
    return customer

async def _process_uploaded_customer_offers_file(db: Session, file_content: bytes, job_id: UUID):
    """
    Background task to process the uploaded customer offers file.
    This function would handle FR1, NFR3 (validation), FR43-FR46 (lead generation, success/error files).
    """
    # In a real application, this would involve more robust file parsing (e.g., pandas)
    # and error handling, writing to success/error files.

    success_records = []
    error_records = []
    
    try:
        decoded_content = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded_content))
        
        # Expected columns (example, based on FR43 product types)
        # This needs to be aligned with the actual template (Ambiguity Q1)
        # Ensure all possible identifiers are included
        expected_columns = [
            "mobile_number", "pan_number", "aadhaar_ref_number", "ucid_number",
            "previous_loan_app_number", "loan_product", "offer_details_json",
            "offer_start_date", "offer_end_date"
        ]
        # Check if all expected columns are in the uploaded file
        if not all(col in csv_reader.fieldnames for col in expected_columns if col != "offer_details_json"):
            raise ValueError(f"Missing one or more required columns. Expected: {expected_columns}")


        for i, row in enumerate(csv_reader):
            row_num = i + 2 # +1 for header, +1 for 0-indexed
            try:
                # Basic column-level validation (FR1, NFR3)
                # Check for required fields and data types
                if not (row.get("mobile_number") or row.get("pan_number") or row.get("aadhaar_ref_number") or
                        row.get("ucid_number") or row.get("previous_loan_app_number")):
                    raise ValueError("At least one identifier (mobile, pan, aadhaar, ucid, prev_loan_app) is required.")
                
                if not row.get("loan_product"):
                    raise ValueError("Loan product is required.")
                
                # Validate loan_product against ProductTypeEnum
                try:
                    loan_product_enum = ProductTypeEnum(row["loan_product"])
                except ValueError:
                    raise ValueError(f"Invalid loan_product: {row['loan_product']}")

                customer_data = {
                    "mobile_number": row.get("mobile_number"),
                    "pan_number": row.get("pan_number"),
                    "aadhaar_ref_number": row.get("aadhaar_ref_number"),
                    "ucid_number": row.get("ucid_number"),
                    "previous_loan_app_number": row.get("previous_loan_app_number"),
                }
                
                offer_details_json = row.get("offer_details_json", "{}")
                try:
                    offer_details = json.loads(offer_details_json)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON in offer_details_json.")

                offer_start_date = None
                if row.get("offer_start_date"):
                    try:
                        offer_start_date = datetime.strptime(row["offer_start_date"], "%Y-%m-%d").date()
                    except ValueError:
                        raise ValueError("Invalid offer_start_date format (YYYY-MM-DD).")

                offer_end_date = None
                if row.get("offer_end_date"):
                    try:
                        offer_end_date = datetime.strptime(row["offer_end_date"], "%Y-%m-%d").date()
                    except ValueError:
                        raise ValueError("Invalid offer_end_date format (YYYY-MM-DD).")

                offer_data = {
                    "product_type": loan_product_enum,
                    "offer_details": offer_details,
                    "offer_start_date": offer_start_date,
                    "offer_end_date": offer_end_date,
                    "offer_type": OfferTypeEnum.FRESH # Assuming uploaded offers are 'Fresh'
                }

                # Call the deduplication and processing logic
                customer = _deduplicate_and_process_offer(db, customer_data, offer_data)
                success_records.append({"row_num": row_num, "customer_id": str(customer.customer_id)})

            except Exception as e:
                error_records.append({"row_num": row_num, "error_desc": str(e), "original_row": row})
                db.rollback() # Rollback any partial transaction for this row

        # After processing all rows, generate success and error files (FR45, FR46)
        # In a real system, these would be stored in a designated location (e.g., S3, local storage)
        # and linked to the job_id for download via another endpoint.
        print(f"Job {job_id}: Processed {len(success_records)} successful records, {len(error_records)} errors.")
        
        # Example of writing to dummy files (in a real app, store these persistently)
        # Success file (FR45)
        with open(f"success_{job_id}.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["row_num", "customer_id"])
            writer.writeheader()
            writer.writerows(success_records)
        
        # Error file (FR46)
        with open(f"error_{job_id}.csv", "w", newline="") as f:
            # Include original row data in error file for debugging
            # Ensure all original row keys are included in fieldnames
            error_fieldnames = ["row_num", "error_desc"] + list(csv_reader.fieldnames)
            writer = csv.DictWriter(f, fieldnames=error_fieldnames)
            writer.writeheader()
            for err_rec in error_records:
                row_to_write = {k: v for k, v in err_rec["original_row"].items()}
                row_to_write["row_num"] = err_rec["row_num"]
                row_to_write["error_desc"] = err_rec["error_desc"]
                writer.writerow(row_to_write)

    except Exception as e:
        print(f"Job {job_id}: Failed to process file due to: {e}")
        # Log the overall file processing error

# --- API Endpoints ---

@router.post("/leads", summary="Receives real-time lead generation data", response_model=CustomerProfileResponse)
async def create_lead(lead_data: LeadCreate, db: Session = Depends(get_db)):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores in CDP.
    Implements FR7, FR11, FR12, FR15, FR16, FR18-FR21, FR25-FR32, FR34.
    """
    # Basic validation for required identifiers
    if not (lead_data.mobile_number or lead_data.pan_number or lead_data.aadhaar_ref_number or
            lead_data.ucid_number or lead_data.previous_loan_app_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one identifier (mobile_number, pan_number, aadhaar_ref_number, ucid_number, previous_loan_app_number) is required."
        )

    customer_data = lead_data.model_dump(exclude={"loan_product", "offer_details", "offer_start_date", "offer_end_date"})
    offer_data = {
        "product_type": lead_data.loan_product,
        "offer_details": lead_data.offer_details,
        "offer_start_date": lead_data.offer_start_date,
        "offer_end_date": lead_data.offer_end_date,
        "offer_type": OfferTypeEnum.FRESH # Real-time leads are typically 'Fresh' offers
    }

    try:
        customer = _deduplicate_and_process_offer(db, customer_data, offer_data)
        
        # After successful processing, potentially push real-time offers to Offermart (FR7, NFR8)
        # This would be an asynchronous call to an external service.
        # Example: await some_offermart_service.push_offer(customer, new_offer)

        # Retrieve the newly created/updated offer for the response
        new_offer = db.query(Offer).filter(
            Offer.customer_id == customer.customer_id,
            Offer.offer_status == OfferStatusEnum.ACTIVE
        ).order_by(Offer.created_at.desc()).first() # Get the most recent active offer

        # Prepare response
        response_customer = CustomerProfileResponse.model_validate(customer)
        if new_offer:
            response_customer.current_offer = OfferResponse.model_validate(new_offer)
        
        # Simplified offer history summary (e.g., last 5 changes)
        history_records = db.query(OfferHistory).filter(
            OfferHistory.customer_id == customer.customer_id
        ).order_by(OfferHistory.change_timestamp.desc()).limit(5).all()
        response_customer.offer_history_summary = [
            {"history_id": str(h.history_id), "offer_id": str(h.offer_id), "new_status": h.new_offer_status, "timestamp": h.change_timestamp}
            for h in history_records
        ]
        response_customer.journey_status = "Journey Started" if new_offer and new_offer.is_journey_started else "Not Started"

        return response_customer

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process lead: {e}")


@router.post("/admin/customer_offers/upload", summary="Upload customer offer details for bulk processing", response_model=CustomerOfferUploadResponse)
async def upload_customer_offers(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV file containing customer offer details."),
    db: Session = Depends(get_db)
):
    """
    Allows administrators to upload a file (e.g., CSV) containing customer offer details
    for bulk processing and lead generation.
    Implements FR43, FR44, FR45, FR46.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are allowed.")

    file_content = await file.read()
    job_id = uuid4()

    # Add the processing task to background tasks
    # Pass a new session to the background task to avoid session conflicts
    # For simplicity, passing the current session, but in production,
    # a new session should be created within the background task.
    background_tasks.add_task(_process_uploaded_customer_offers_file, db, file_content, job_id)

    return CustomerOfferUploadResponse(
        status="success",
        message="File uploaded successfully. Processing started in the background.",
        job_id=job_id
    )

@router.get("/admin/campaigns/moengage_file", summary="Generates and provides the latest Moengage-formatted campaign file", response_class=StreamingResponse)
async def get_moengage_file(db: Session = Depends(get_db)):
    """
    Generates and provides the latest Moengage-formatted campaign file in CSV format for download.
    Implements FR39, FR54, FR55.
    """
    # FR54: Generate a Moengage format file in .csv format.
    # This involves querying active offers and customer data, then formatting it.
    # The exact fields for Moengage file are not specified (Ambiguity Q10, Q11),
    # so we'll use a plausible set of fields.

    # Query active offers and their associated customer data
    # Consider only 'Active' offers that are not DND
    offers_for_moengage = db.query(Offer, Customer).join(Customer).filter(
        Offer.offer_status == OfferStatusEnum.ACTIVE,
        Offer.is_journey_started == False, # Only for non-journey started customers (implied by campaign purpose)
        Customer.dnd_status == False # FR34: Avoid DND customers
    ).all()

    output = io.StringIO()
    # Example Moengage fields (these would be defined by the Moengage team - Ambiguity Q10, Q11)
    fieldnames = [
        "customer_id", "mobile_number", "pan_number", "aadhaar_ref_number",
        "offer_id", "product_type", "offer_status", "offer_start_date", "offer_end_date",
        "offer_details_json", "customer_segments", "propensity_flag"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)

    writer.writeheader()
    for offer, customer in offers_for_moengage:
        row = {
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan_number": customer.pan_number,
            "aadhaar_ref_number": customer.aadhaar_ref_number,
            "offer_id": str(offer.offer_id),
            "product_type": offer.product_type.value,
            "offer_status": offer.offer_status.value,
            "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else "",
            "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else "",
            "offer_details_json": json.dumps(offer.offer_details),
            "customer_segments": ",".join(customer.customer_segments) if customer.customer_segments else "",
            "propensity_flag": customer.propensity_flag
        }
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')), # Encode to bytes for StreamingResponse
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=moengage_campaign_file.csv"}
    )

@router.get("/customers/{customer_id}", summary="Retrieves a single profile view of a customer", response_model=CustomerProfileResponse)
async def get_customer_profile(customer_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieves a single profile view of a customer, including their current offers,
    attributes, segments, and journey stages.
    Implements FR2, FR23, FR24, FR50.
    """
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    # Get current active offer
    current_offer = db.query(Offer).filter(
        Offer.customer_id == customer_id,
        Offer.offer_status == OfferStatusEnum.ACTIVE
    ).order_by(Offer.created_at.desc()).first()

    # Get offer history for the past 6 months (FR23)
    six_months_ago = datetime.now() - timedelta(days=180)
    offer_history_records = db.query(OfferHistory).filter(
        OfferHistory.customer_id == customer_id,
        OfferHistory.change_timestamp >= six_months_ago
    ).order_by(OfferHistory.change_timestamp.desc()).all()

    # Prepare response model
    response_customer = CustomerProfileResponse.model_validate(customer)
    if current_offer:
        response_customer.current_offer = OfferResponse.model_validate(current_offer)
        response_customer.journey_status = "Journey Started" if current_offer.is_journey_started else "Not Started"
    else:
        response_customer.current_offer = None
        response_customer.journey_status = "No Active Offer"

    response_customer.offer_history_summary = [
        {
            "history_id": str(h.history_id),
            "offer_id": str(h.offer_id),
            "old_status": h.old_offer_status,
            "new_status": h.new_offer_status,
            "reason": h.change_reason,
            "timestamp": h.change_timestamp
        }
        for h in offer_history_records
    ]

    return response_customer