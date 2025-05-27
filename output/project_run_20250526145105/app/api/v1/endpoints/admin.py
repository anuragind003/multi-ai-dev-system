import io
import uuid
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models import models as db_models
from app.services import admin_service

router = APIRouter()

# In-memory store for job results (for demonstration purposes only).
# In a production environment, this should be replaced with a persistent store
# like a database table, Redis, or a dedicated file storage system (e.g., S3, Azure Blob Storage).
# Structure: {job_id: {"status": "pending"|"processing"|"completed"|"failed",
#                       "message": "...",
#                       "success_file_content": bytes, # Raw bytes of the Excel file
#                       "error_file_content": bytes}} # Raw bytes of the Excel file
job_results_store = {}

@router.post("/customer_offers/upload", summary="Upload customer offer details for bulk processing")
async def upload_customer_offers(
    file: UploadFile = File(..., description="CSV or Excel file containing customer offer details"),
    background_tasks: BackgroundTasks = Depends(),
    db: Session = Depends(get_db)
):
    """
    Allows administrators to upload a file (CSV or Excel) containing customer offer details
    for bulk processing, deduplication, and lead generation.

    The processing is handled in a background task to prevent blocking the API response.
    A job ID is returned to track the status and retrieve generated files.

    - **FR43**: Allows uploading customer details for Prospect, TW Loyalty, Topup, Employee loans.
    - **FR44**: Generates leads upon successful upload.
    - **FR45**: Generates a success file.
    - **FR46**: Generates an error file with 'Error Desc' column.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    # Validate file extension
    allowed_extensions = (".csv", ".xlsx")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Only {', '.join(allowed_extensions)} files are supported."
        )

    job_id = str(uuid.uuid4())
    job_results_store[job_id] = {"status": "pending", "message": "File upload received, processing initiated."}

    # Read file content into memory. This is suitable for smaller files.
    # For very large files, consider streaming directly to a temporary disk location.
    try:
        file_content = await file.read()
        file_like_object = io.BytesIO(file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read uploaded file: {str(e)}")

    # Add the processing task to background.
    # The actual heavy lifting (reading, parsing, DB operations) happens here.
    background_tasks.add_task(
        admin_service.process_customer_offer_upload,
        job_id,
        file_like_object,
        file.filename,
        db,
        job_results_store
    )

    return JSONResponse(
        status_code=202, # 202 Accepted: The request has been accepted for processing, but the processing has not been completed.
        content={
            "status": "success",
            "message": "File uploaded successfully. Processing initiated in background.",
            "job_id": job_id
        }
    )

@router.get("/campaigns/moengage_file", summary="Download Moengage-formatted campaign file")
async def download_moengage_file(db: Session = Depends(get_db)):
    """
    Generates and provides the latest Moengage-formatted campaign file in CSV format for download.
    This file includes campaign-ready customer and offer data.

    - **FR39**: Allows users to download the Moengage File.
    - **FR54**: Generates a Moengage format file in .csv format.
    - **FR55**: Provides a front-end utility for LTFS users to download the generated Moengage format file.
    """
    try:
        csv_data = admin_service.generate_moengage_file_data(db)
        
        # If no data is found, return an appropriate message instead of an empty file
        if not csv_data.strip(): # Check if CSV data is empty or just whitespace
            raise HTTPException(status_code=404, detail="No active campaign data found to generate Moengage file.")

        response = StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f"attachment; filename=moengage_campaign_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return response
    except HTTPException:
        raise # Re-raise HTTPExceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Moengage file: {str(e)}")

@router.get("/downloads/unique_data", summary="Download unique customer data file")
async def download_unique_data(db: Session = Depends(get_db)):
    """
    Allows users to download a file containing unique customer data in CSV format.

    - **FR41**: Allows users to download the Unique Data File.
    """
    try:
        csv_data = admin_service.get_unique_customer_data(db)
        
        if not csv_data.strip():
            raise HTTPException(status_code=404, detail="No unique customer data found.")

        response = StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f"attachment; filename=unique_customer_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate unique data file: {str(e)}")

@router.get("/downloads/duplicate_data", summary="Download duplicate customer data file")
async def download_duplicate_data(db: Session = Depends(get_db)):
    """
    Allows users to download a file containing duplicate customer data in CSV format.
    This file helps in reviewing and managing duplicate records.

    - **FR40**: Allows users to download the Duplicate Data File.
    """
    try:
        csv_data = admin_service.get_duplicate_customer_data(db)
        
        if not csv_data.strip():
            raise HTTPException(status_code=404, detail="No duplicate customer data found.")

        response = StreamingResponse(
            io.StringIO(csv_data),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f"attachment; filename=duplicate_customer_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate duplicate data file: {str(e)}")

@router.get("/uploads/{job_id}/status", summary="Get status of an upload job")
async def get_upload_job_status(job_id: str):
    """
    Retrieves the current status of a customer offer upload job initiated via the
    `/customer_offers/upload` endpoint.
    """
    job_status = job_results_store.get(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    
    # Return a copy to prevent external modification of the store
    return JSONResponse(content=job_status.copy())

@router.get("/downloads/error_file/{job_id}", summary="Download error file for a specific upload job")
async def download_error_file(job_id: str):
    """
    Allows users to download the error Excel file generated during a data upload
    on the Admin Portal, identified by a job ID.

    - **FR42**: Allows users to download the Error Excel.
    """
    job_status = job_results_store.get(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    
    if job_status.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Job is still processing or has not completed yet.")
    
    error_file_content = job_status.get("error_file_content")
    if not error_file_content:
        raise HTTPException(status_code=404, detail="No error file generated for this job or it was empty.")

    # In a real application, you might want to delete the file from storage
    # after it's downloaded, or implement a proper retention policy.
    # job_results_store[job_id]["error_file_content"] = None # Uncomment to clear after download

    response = StreamingResponse(
        io.BytesIO(error_file_content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" # For Excel
    )
    response.headers["Content-Disposition"] = f"attachment; filename=error_report_{job_id}.xlsx"
    return response

@router.get("/downloads/success_file/{job_id}", summary="Download success file for a specific upload job")
async def download_success_file(job_id: str):
    """
    Allows users to download the success Excel file generated after a successful data upload
    on the Admin Portal, identified by a job ID.

    - **FR45**: Generates a success file upon successful data upload.
    """
    job_status = job_results_store.get(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    
    if job_status.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Job is still processing or has not completed yet.")
    
    success_file_content = job_status.get("success_file_content")
    if not success_file_content:
        raise HTTPException(status_code=404, detail="No success file generated for this job or it was empty.")

    # In a real application, you might want to delete the file from storage
    # after it's downloaded, or implement a proper retention policy.
    # job_results_store[job_id]["success_file_content"] = None # Uncomment to clear after download

    response = StreamingResponse(
        io.BytesIO(success_file_content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" # For Excel
    )
    response.headers["Content-Disposition"] = f"attachment; filename=success_report_{job_id}.xlsx"
    return response