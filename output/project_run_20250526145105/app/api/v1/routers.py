from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import io
import datetime

# Assuming these modules exist and contain the necessary classes/functions
# app.database for database session dependency
# app.schemas for Pydantic request/response models
# app.services for business logic functions
from app.database import get_db
from app.schemas import LeadCreate, CustomerResponse, UploadResponse, DailyTallyReport, OfferSummary
from app.services import customer_service, admin_service, report_service

router = APIRouter()

@router.post("/leads", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores in CDP.
    """
    try:
        customer_id = await customer_service.process_lead(db, lead)
        return {
            "status": "success",
            "message": "Lead processed and stored",
            "customer_id": customer_id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # In a real application, you would log the full exception details here
        print(f"Error processing lead: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process lead due to an internal error.")

@router.post("/admin/customer_offers/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_customer_offers(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Allows administrators to upload a file (e.g., CSV) containing customer offer details
    for bulk processing and lead generation.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded."
        )
    if not (file.filename.endswith(".csv") or file.filename.endswith(".xlsx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only CSV or Excel files (.csv, .xlsx) are allowed."
        )

    # Read file content
    file_content = await file.read()

    try:
        # The service function will handle saving the file temporarily or processing directly from content
        job_id = await admin_service.initiate_customer_offers_upload(db, file.filename, file_content, background_tasks)
        return {
            "status": "success",
            "message": "File uploaded, processing started in background",
            "job_id": job_id
        }
    except Exception as e:
        print(f"Error initiating file upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to initiate file upload: {e}")


@router.get("/admin/campaigns/moengage_file", response_class=StreamingResponse)
async def get_moengage_file(db: Session = Depends(get_db)):
    """
    Generates and provides the latest Moengage-formatted campaign file in CSV format for download.
    """
    try:
        csv_data = await admin_service.generate_moengage_file(db)
        if not csv_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Moengage data available to generate file.")

        # Create a file-like object from the string data
        file_like_object = io.StringIO(csv_data)

        return StreamingResponse(
            file_like_object,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=moengage_campaign_data_{datetime.date.today().isoformat()}.csv"
            }
        )
    except Exception as e:
        print(f"Error generating Moengage file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate Moengage file: {e}")

@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer_profile(customer_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieves a single profile view of a customer, including their current offers,
    attributes, segments, and journey stages.
    """
    # Assume customer_service.get_customer_profile returns a dictionary that
    # directly matches the CustomerResponse schema structure, including nested objects.
    customer_data = await customer_service.get_customer_profile(db, customer_id)
    if not customer_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    return CustomerResponse(**customer_data)


@router.get("/reports/daily_tally", response_model=DailyTallyReport)
async def get_daily_tally_report(
    report_date: Optional[datetime.date] = None,
    db: Session = Depends(get_db)
):
    """
    Provides daily summary reports for data tally, including counts of unique customers,
    offers, and processed records.
    """
    if report_date is None:
        report_date = datetime.date.today()

    report_data = await report_service.get_daily_tally_report(db, report_date)
    if not report_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report data not found for the specified date.")

    return DailyTallyReport(**report_data)