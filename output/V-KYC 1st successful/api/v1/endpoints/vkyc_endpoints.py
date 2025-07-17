import logging
from typing import List
from fastapi import APIRouter, Depends, status, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    VKYCSearchRequest, VKYCSearchResponse, VKYCRecordingResponse,
    BulkDownloadRequest, Token, User
)
from app.services.vkyc_service import VKYCService
from app.auth import authenticate_user, get_current_user, has_role
from app.security import create_access_token
from app.config import settings
from app.exceptions import ValidationException, NotFoundException, FileOperationException

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Authentication Endpoint ---
@router.post("/token", response_model=Token, summary="Authenticate User and Get JWT Token", tags=["Authentication"])
async def login_for_access_token(username: str = Depends(lambda form_data: form_data.username),
                                 password: str = Depends(lambda form_data: form_data.password)):
    """
    Authenticates a user with username and password and returns a JWT access token.
    """
    user = await authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles}
    )
    logger.info(f"User '{username}' successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

# --- VKYC Endpoints ---
@router.post(
    "/vkyc/search",
    response_model=VKYCSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search VKYC Recordings",
    description="Searches for VKYC recordings based on various criteria with pagination. "
                "Requires 'tl' or 'process_manager' role.",
    tags=["VKYC Recordings"],
    dependencies=[Depends(has_role(["tl", "process_manager"]))]
)
async def search_vkyc_recordings(
    request: VKYCSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Search VKYC Recordings**

    Allows users with 'tl' or 'process_manager' roles to search for VKYC recordings.
    Supports filtering by:
    - `query`: General search across LAN ID, customer name, agent ID.
    - `lan_id`: Specific LAN ID.
    - `agent_id`: Specific Agent ID.
    - `customer_name`: Specific Customer Name.
    - `start_date`, `end_date`: Date range for upload date (YYYY-MM-DD).
    - `status`: Recording status (e.g., 'completed', 'pending').
    - `page`, `page_size`: For pagination.

    **Performance Note:** This endpoint includes caching for search results to improve response times for repeated queries.
    """
    logger.info(f"User '{current_user.username}' performing search with criteria: {request.model_dump()}")
    service = VKYCService(db)
    records, total_records = await service.search_recordings(request)
    
    return VKYCSearchResponse(
        total_records=total_records,
        page=request.page,
        page_size=request.page_size,
        records=records
    )

@router.get(
    "/vkyc/download/{lan_id}",
    summary="Download Single VKYC Recording",
    description="Downloads a single VKYC recording file by its LAN ID. "
                "Requires 'tl' or 'process_manager' role.",
    tags=["VKYC Recordings"],
    dependencies=[Depends(has_role(["tl", "process_manager"]))]
)
async def download_vkyc_recording(
    lan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Download Single VKYC Recording**

    Allows users with 'tl' or 'process_manager' roles to download a specific VKYC recording.
    The file is streamed directly from the simulated NFS path.

    **Performance Note:** This endpoint simulates file I/O latency to mimic real-world NFS performance.
    """
    logger.info(f"User '{current_user.username}' requesting download for LAN ID: {lan_id}")
    service = VKYCService(db)
    
    try:
        file_full_path, file_name = await service.download_recording(lan_id)
        
        def file_iterator():
            with open(file_full_path, "rb") as f:
                while chunk := f.read(8192): # Read in chunks
                    yield chunk

        logger.info(f"Streaming file '{file_name}' for LAN ID '{lan_id}'.")
        return StreamingResponse(
            file_iterator(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=\"{file_name}\""}
        )
    except NotFoundException as e:
        logger.warning(f"Download failed for LAN ID '{lan_id}': {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except FileOperationException as e:
        logger.error(f"File operation error during download for LAN ID '{lan_id}': {e.detail}", exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.critical(f"Unexpected error during download for LAN ID '{lan_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during download.")


@router.post(
    "/vkyc/bulk-download",
    summary="Bulk Download VKYC Recordings",
    description="Downloads multiple VKYC recording files as a ZIP archive. "
                "Maximum 10 LAN IDs per request. Requires 'tl' or 'process_manager' role.",
    tags=["VKYC Recordings"],
    dependencies=[Depends(has_role(["tl", "process_manager"]))]
)
async def bulk_download_vkyc_recordings(
    request: BulkDownloadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    **Bulk Download VKYC Recordings**

    Allows users with 'tl' or 'process_manager' roles to download multiple VKYC recordings
    as a single ZIP file.
    - Input: A list of `lan_ids` (maximum 10).

    **Performance Note:** This endpoint simulates file I/O latency for each file and
    then zips them on the fly. This can be resource-intensive for large numbers of files or very large files.
    """
    logger.info(f"User '{current_user.username}' requesting bulk download for {len(request.lan_ids)} LAN IDs.")
    service = VKYCService(db)

    try:
        zip_buffer, zip_file_name = await service.bulk_download_recordings(request.lan_ids)
        
        logger.info(f"Streaming bulk download zip file: {zip_file_name}")
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=\"{zip_file_name}\""}
        )
    except ValidationException as e:
        logger.warning(f"Bulk download validation error: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except NotFoundException as e:
        logger.warning(f"Bulk download failed: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except FileOperationException as e:
        logger.error(f"File operation error during bulk download: {e.detail}", exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.critical(f"Unexpected error during bulk download: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during bulk download.")