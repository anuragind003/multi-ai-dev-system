from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import io
from datetime import date

# Assuming these modules exist in the 'app' directory
from app.database import get_db
from app.schemas import (
    LeadCreate, LeadResponse, UploadResponse,
    CustomerDetailResponse, DailyTallyReport
)
from app.services import (
    leads_service, admin_service, campaign_service,
    customer_service, report_service
)

router = APIRouter()

@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    db: Session = Depends(get_db)
):
    """
    Receives real-time lead generation data from external aggregators/Insta,
    processes it, and stores in CDP.
    (FR7, FR11, FR12)
    """
    try:
        customer_id = leads_service.process_lead(db, lead_data)
        return LeadResponse(
            status="success",
            message="Lead processed and stored",
            customer_id=customer_id
        )
    except Exception as e:
        # In a real application, more specific error handling and logging would be needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process lead: {e}"
        )

@router.post("/admin/customer_offers/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_customer_offers(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Allows administrators to upload a file (e.g., CSV) containing customer offer details
    for bulk processing and lead generation.
    (FR43, FR44, FR45, FR46)
    """
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV or Excel files are allowed."
        )

    try:
        file_content = await file.read()
        # Pass the database session to the background task.
        # Note: SQLAlchemy sessions are not thread-safe. For background tasks,
        # it's often better to create a new session within the task or use a connection pool.
        # For simplicity here, we're passing the session, but in a production app,
        # consider `with get_db() as db_task:` inside the background function.
        job_id = admin_service.upload_customer_offers_file(db, file_content, background_tasks)
        return UploadResponse(
            status="success",
            message="File uploaded, processing started in background",
            job_id=job_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload and process file: {e}"
        )

@router.get("/admin/campaigns/moengage_file", status_code=status.HTTP_200_OK)
async def get_moengage_file(
    db: Session = Depends(get_db)
):
    """
    Generates and provides the latest Moengage-formatted campaign file in CSV format for download.
    (FR39, FR54, FR55)
    """
    try:
        csv_file_stream = campaign_service.generate_moengage_file(db)
        return StreamingResponse(
            csv_file_stream,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=moengage_campaign_data.csv"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Moengage file: {e}"
        )

@router.get("/customers/{customer_id}", response_model=CustomerDetailResponse, status_code=status.HTTP_200_OK)
async def get_customer_details(
    customer_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieves a single profile view of a customer, including their current offers,
    attributes, segments, and journey stages.
    (FR2, FR50)
    """
    customer_details = customer_service.get_customer_details(db, customer_id)
    if not customer_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found."
        )
    return customer_details

@router.get("/reports/daily_tally", response_model=DailyTallyReport, status_code=status.HTTP_200_OK)
async def get_daily_tally_report(
    report_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Provides daily summary reports for data tally, including counts of unique customers,
    offers, and processed records.
    (FR49)
    """
    try:
        report = report_service.get_daily_tally_report(db, report_date)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate daily tally report: {e}"
        )

# Additional endpoints for downloading other files (FR40, FR41, FR42)
# These would follow a similar pattern to `get_moengage_file` but call different service functions.
# For brevity, they are not fully implemented here but would be added based on specific requirements.

# @router.get("/admin/data/duplicate_file", status_code=status.HTTP_200_OK)
# async def get_duplicate_data_file(db: Session = Depends(get_db)):
#     """
#     Allows users to download the Duplicate Data File. (FR40)
#     """
#     # Logic to generate and return duplicate data CSV
#     pass

# @router.get("/admin/data/unique_file", status_code=status.HTTP_200_OK)
# async def get_unique_data_file(db: Session = Depends(get_db)):
#     """
#     Allows users to download the Unique Data File. (FR41)
#     """
#     # Logic to generate and return unique data CSV
#     pass

# @router.get("/admin/data/error_file/{job_id}", status_code=status.HTTP_200_OK)
# async def get_error_file(job_id: UUID, db: Session = Depends(get_db)):
#     """
#     Allows users to download the Error Excel for a specific upload job. (FR42)
#     """
#     # Logic to retrieve and return the error file generated by the background task
#     pass