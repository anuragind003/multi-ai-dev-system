from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID, uuid4
import pandas as pd
import io
from datetime import date

# Assuming these modules exist in the project structure
# Adjust imports based on actual file paths if different
from app.database import get_async_db
from app.schemas.offer import (
    LeadCreate, LeadResponse, CustomerOfferUploadResponse,
    OfferDetailsSchema, OfferStatusEnum, OfferTypeEnum, ProductTypeEnum
)
from app.schemas.customer import CustomerResponse
from app.crud.customer import (
    get_customer_by_identifiers, create_customer, update_customer_attributes,
    get_customer_dnd_status
)
from app.crud.offer import (
    create_offer, get_active_offer_for_customer, update_offer_status,
    create_offer_history
)
from app.models.customer import Customer
from app.models.offer import Offer

router = APIRouter()

# Helper function for offer processing logic (can be moved to a service layer later)
async def process_single_offer(
    db: AsyncSession,
    mobile_number: str,
    pan_number: Optional[str],
    aadhaar_ref_number: Optional[str],
    ucid_number: Optional[str],
    previous_loan_app_number: Optional[str],
    loan_product: ProductTypeEnum,
    offer_details: OfferDetailsSchema,
    offer_type: OfferTypeEnum,
    offer_start_date: Optional[date] = None,
    offer_end_date: Optional[date] = None,
    source: str = "API" # e.g., "API", "Admin_Upload"
) -> CustomerResponse:
    """
    Processes a single offer, including deduplication, DND check, and offer precedence.
    Returns the customer response with the associated offer.
    """
    # 1. Deduplication (FR2, FR3, FR4, FR5, FR6)
    existing_customer = await get_customer_by_identifiers(
        db, mobile_number, pan_number, aadhaar_ref_number, ucid_number, previous_loan_app_number
    )

    customer: Customer
    if existing_customer:
        customer = existing_customer
        # Update customer attributes if new data is richer (e.g., from Offermart)
        # For simplicity, we'll just use the existing customer.
        # In a real scenario, merge/update customer_attributes.
        await update_customer_attributes(db, customer.customer_id, {
            "mobile_number": mobile_number,
            "pan_number": pan_number,
            "aadhaar_ref_number": aadhaar_ref_number,
            "ucid_number": ucid_number,
            "previous_loan_app_number": previous_loan_app_number,
            # Add other attributes from offer_details if they belong to customer
        })
    else:
        customer = await create_customer(
            db,
            mobile_number=mobile_number,
            pan_number=pan_number,
            aadhaar_ref_number=aadhaar_ref_number,
            ucid_number=ucid_number,
            previous_loan_app_number=previous_loan_app_number,
            customer_attributes={}, # Initialize, can be enriched later
            customer_segments=[],
            propensity_flag=None,
            dnd_status=False # Default, will be checked below
        )

    # 2. DND Check (FR34)
    if await get_customer_dnd_status(db, customer.customer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Customer {customer.customer_id} is on DND list. Offer cannot be processed."
        )

    # 3. Offer Precedence and Conflict Resolution (FR15, FR19, FR20, FR21, FR25-FR32)
    active_offer = await get_active_offer_for_customer(db, customer.customer_id)

    new_offer_status = OfferStatusEnum.ACTIVE
    new_offer_reason = f"New {offer_type.value} offer from {source}"

    if active_offer:
        if active_offer.is_journey_started:
            # FR15: Prevent modification if journey started.
            # FR21: If Enrich offer's journey has started, it shall not flow into CDP.
            if offer_type == OfferTypeEnum.ENRICH:
                new_offer_status = OfferStatusEnum.REJECTED
                new_offer_reason = "Rejected: Enrich offer for customer with active journey."
            else:
                # FR26, FR27, FR28: Direct to existing offer, attribution remains.
                # For simplicity, we'll mark the new offer as duplicate/rejected.
                new_offer_status = OfferStatusEnum.DUPLICATE
                new_offer_reason = "Duplicate: Customer has an active offer with started journey."
                # The existing active offer prevails.
                # We might still log this attempt as a campaign event.
                # For now, we'll create a 'DUPLICATE' offer record.

        elif offer_type == OfferTypeEnum.ENRICH:
            # FR20: If an Enrich offer's journey has not started, it shall flow to CDP,
            # and the previous offer will be moved to Duplicate.
            await update_offer_status(
                db, active_offer.offer_id, OfferStatusEnum.DUPLICATE,
                reason="Replaced by new Enrich offer (journey not started)."
            )
            new_offer_status = OfferStatusEnum.ACTIVE
            new_offer_reason = "Active: New Enrich offer replacing old inactive journey offer."
        else:
            # FR25, FR29, FR30, FR31, FR32: Complex precedence rules.
            # For MVP, if an active offer exists without a started journey,
            # and the new offer is not 'Enrich', we'll generally mark the new one as duplicate.
            # A more sophisticated system would compare product types and offer values.
            new_offer_status = OfferStatusEnum.DUPLICATE
            new_offer_reason = "Duplicate: Customer has an active offer without started journey (new offer not Enrich)."
            # The existing active offer prevails.
            # We might still log this attempt as a campaign event.
            # For now, we'll create a 'DUPLICATE' offer record.

    # Create the new offer record
    new_offer = await create_offer(
        db,
        customer_id=customer.customer_id,
        offer_type=offer_type,
        offer_status=new_offer_status,
        product_type=loan_product,
        offer_details=offer_details.model_dump(mode='json'), # Convert Pydantic model to dict
        offer_start_date=offer_start_date or date.today(),
        offer_end_date=offer_end_date or date.today().replace(year=date.today().year + 1), # Default to 1 year validity
        is_journey_started=False, # Always false initially for new offers
        loan_application_id=None
    )

    # Create offer history entry for the new offer
    await create_offer_history(
        db,
        offer_id=new_offer.offer_id,
        customer_id=customer.customer_id,
        old_offer_status=None, # No old status for a new offer
        new_offer_status=new_offer_status,
        change_reason=new_offer_reason,
        snapshot_offer_details=new_offer.offer_details
    )

    # If the new offer was marked as DUPLICATE/REJECTED, the prevailing offer is the old one (if any)
    # or no offer if the customer was new and the offer was rejected for DND.
    # For the response, we return the customer and the *newly created* offer's status.
    # The frontend/calling system can then interpret this status.
    return CustomerResponse(
        customer_id=customer.customer_id,
        mobile_number=customer.mobile_number,
        pan_number=customer.pan_number,
        aadhaar_ref_number=customer.aadhaar_ref_number,
        current_offer={
            "offer_id": new_offer.offer_id,
            "product_type": new_offer.product_type,
            "offer_status": new_offer.offer_status,
            "offer_type": new_offer.offer_type,
            "is_journey_started": new_offer.is_journey_started
        },
        journey_status="N/A", # This would come from campaign_events or LOS integration
        segments=customer.customer_segments
    )


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_200_OK)
async def create_lead_offer(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores in CDP.
    """
    try:
        customer_response = await process_single_offer(
            db,
            mobile_number=lead_data.mobile_number,
            pan_number=lead_data.pan_number,
            aadhaar_ref_number=lead_data.aadhaar_ref_number,
            ucid_number=lead_data.ucid_number,
            previous_loan_app_number=lead_data.previous_loan_app_number,
            loan_product=lead_data.loan_product,
            offer_details=lead_data.offer_details,
            offer_type=OfferTypeEnum.FRESH, # Real-time leads are typically 'Fresh'
            offer_start_date=lead_data.offer_details.offer_start_date,
            offer_end_date=lead_data.offer_details.offer_end_date,
            source="API"
        )
        return LeadResponse(
            status="success",
            message="Lead processed and stored",
            customer_id=customer_response.customer_id,
            offer_status=customer_response.current_offer["offer_status"]
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process lead: {str(e)}"
        )

async def process_uploaded_offers_background(
    db: AsyncSession,
    file_content: bytes,
    file_type: str,
    job_id: UUID
):
    """
    Background task to process uploaded customer offer files.
    """
    success_records = []
    error_records = []
    df: pd.DataFrame

    try:
        if file_type == "csv":
            df = pd.read_csv(io.BytesIO(file_content))
        elif file_type in ["xlsx", "xls"]:
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError("Unsupported file type.")

        # Basic validation: Check for required columns
        required_columns = [
            "mobile_number", "loan_product", "offer_type",
            "offer_amount", "interest_rate", "tenure_months",
            "offer_start_date", "offer_end_date"
        ]
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Missing required columns. Expected: {', '.join(required_columns)}")

        # Convert relevant columns to string to avoid type issues with Pydantic
        df['mobile_number'] = df['mobile_number'].astype(str)
        if 'pan_number' in df.columns: df['pan_number'] = df['pan_number'].astype(str).replace('nan', None)
        if 'aadhaar_ref_number' in df.columns: df['aadhaar_ref_number'] = df['aadhaar_ref_number'].astype(str).replace('nan', None)
        if 'ucid_number' in df.columns: df['ucid_number'] = df['ucid_number'].astype(str).replace('nan', None)
        if 'previous_loan_app_number' in df.columns: df['previous_loan_app_number'] = df['previous_loan_app_number'].astype(str).replace('nan', None)

        # Convert date columns
        for col in ['offer_start_date', 'offer_end_date']:
            if col in df.columns:
                # Use errors='coerce' to turn unparseable dates into NaT (Not a Time)
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        for index, row in df.iterrows():
            try:
                # Prepare offer_details from row, including dynamic fields
                offer_details_dict = {
                    "offer_amount": row.get("offer_amount"),
                    "interest_rate": row.get("interest_rate"),
                    "tenure_months": row.get("tenure_months"),
                    "offer_start_date": row.get("offer_start_date"),
                    "offer_end_date": row.get("offer_end_date"),
                    # Include any other columns from the Excel as part of offer_details
                    **{k: v for k, v in row.items() if k not in required_columns and k not in ["pan_number", "aadhaar_ref_number", "ucid_number", "previous_loan_app_number", "mobile_number", "loan_product", "offer_type"]}
                }
                
                # Filter out None values from offer_details_dict before passing to Pydantic
                offer_details_dict = {k: v for k, v in offer_details_dict.items() if v is not None}

                offer_details_schema = OfferDetailsSchema(**offer_details_dict)

                customer_response = await process_single_offer(
                    db,
                    mobile_number=row["mobile_number"],
                    pan_number=row.get("pan_number"),
                    aadhaar_ref_number=row.get("aadhaar_ref_number"),
                    ucid_number=row.get("ucid_number"),
                    previous_loan_app_number=row.get("previous_loan_app_number"),
                    loan_product=ProductTypeEnum(row["loan_product"]), # Ensure enum conversion
                    offer_type=OfferTypeEnum(row["offer_type"]), # Ensure enum conversion
                    offer_start_date=row.get("offer_start_date"),
                    offer_end_date=row.get("offer_end_date"),
                    source="Admin_Upload"
                )
                success_records.append({
                    "row_index": index,
                    "mobile_number": row["mobile_number"],
                    "customer_id": str(customer_response.customer_id),
                    "offer_status": customer_response.current_offer["offer_status"],
                    "message": "Processed successfully"
                })
            except HTTPException as he:
                error_records.append({
                    "row_index": index,
                    "mobile_number": row["mobile_number"],
                    "error_desc": he.detail
                })
            except Exception as e:
                error_records.append({
                    "row_index": index,
                    "mobile_number": row["mobile_number"],
                    "error_desc": str(e)
                })
    except Exception as e:
        # Handle file parsing or initial validation errors
        error_records.append({
            "row_index": "N/A",
            "mobile_number": "N/A",
            "error_desc": f"File processing error: {str(e)}"
        })

    # In a real system, these files would be saved to a persistent storage (e.g., S3, local disk)
    # and a link would be provided to the user via a separate endpoint or notification.
    # For this MVP, we'll just print/log them.
    print(f"Job {job_id} - Success Records: {len(success_records)}")
    print(f"Job {job_id} - Error Records: {len(error_records)}")

    # TODO: Implement actual storage of success/error files and job status
    # For example, save to a 'job_results' table or a designated file storage.
    # This would allow the frontend to query the status and download results later.


@router.post("/admin/customer_offers/upload", response_model=CustomerOfferUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_customer_offers(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_async_db) # Inject db for background task
):
    """
    Allows administrators to upload a file (e.g., CSV/Excel) containing customer offer details
    for bulk processing and lead generation.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded.")

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["csv", "xlsx", "xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only CSV, XLSX, XLS are allowed."
        )

    job_id = uuid4()
    file_content = await file.read()

    # Add the processing function to background tasks
    # Note: Passing db session to background tasks requires careful management.
    # For a simple example, we pass it directly. In a production system,
    # you might want to create a new session within the background task or use a task queue.
    background_tasks.add_task(process_uploaded_offers_background, db, file_content, file_extension, job_id)

    return CustomerOfferUploadResponse(
        status="success",
        message="File uploaded successfully. Processing started in the background.",
        job_id=job_id
    )

# TODO: Add endpoint for downloading success/error files based on job_id (FR38, FR45, FR46)
# This would require a mechanism to store the results of the background task persistently.
# For example:
# @router.get("/admin/customer_offers/upload_status/{job_id}")
# async def get_upload_status(job_id: UUID, db: AsyncSession = Depends(get_async_db)):
#     # Retrieve job status and file paths from a job_results table
#     pass

# @router.get("/admin/customer_offers/download_success/{job_id}")
# async def download_success_file(job_id: UUID, db: AsyncSession = Depends(get_async_db)):
#     # Retrieve success file content and return as FileResponse
#     pass

# @router.get("/admin/customer_offers/download_error/{job_id}")
# async def download_error_file(job_id: UUID, db: AsyncSession = Depends(get_async_db)):
#     # Retrieve error file content and return as FileResponse
#     pass