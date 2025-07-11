import logging
from fastapi import APIRouter, UploadFile, File, status
from fastapi.responses import JSONResponse
from schemas import FileUploadResponse, FileUploadStatusResponse
from dependencies import CurrentUser, FileParserServiceDep, DBSession
from models import FileUpload
from core.exceptions import NotFoundException

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/file-uploads",
    tags=["File Uploads"],
    responses={404: {"description": "Not found"}},
)

@router.post(
    "/upload-lan-ids",
    response_model=FileUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a CSV/TXT file with LAN IDs for parsing and validation",
    description="""
    Uploads a CSV or TXT file containing LAN IDs.
    The system will parse the file, validate each LAN ID against a predefined pattern,
    and check the total count of IDs (min 2, max 50).
    The upload process is asynchronous, and a record of the upload is stored.
    Returns a summary of valid and invalid LAN IDs.
    """
)
async def upload_lan_ids(
    file: UploadFile = File(..., description="CSV or TXT file containing LAN IDs. Max 5MB."),
    current_user: CurrentUser = None, # Requires authentication
    file_parser_service: FileParserServiceDep = None,
):
    """
    Handles the upload of a file containing LAN IDs.
    """
    log.info(f"Received file upload request for '{file.filename}' from user '{current_user.username}'")
    
    # The actual parsing and validation logic is handled by the service.
    # The service also persists the upload metadata to the database.
    processing_result = await file_parser_service.parse_and_validate_file(file, current_user.username)
    
    log.info(f"File '{file.filename}' processed. Upload ID: {processing_result['upload_id']}")
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=processing_result
    )

@router.get(
    "/{upload_id}",
    response_model=FileUploadStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get status and details of a specific file upload",
    description="Retrieves the full details, including valid and invalid LAN IDs, for a given file upload ID."
)
async def get_upload_status(
    upload_id: int,
    current_user: CurrentUser = None, # Requires authentication
    db: DBSession = None,
):
    """
    Retrieves the status and details of a previously uploaded file.
    """
    log.info(f"Fetching upload status for ID: {upload_id} by user '{current_user.username}'")
    file_upload = db.query(FileUpload).filter(FileUpload.id == upload_id).first()

    if not file_upload:
        log.warning(f"File upload with ID {upload_id} not found.")
        raise NotFoundException(detail=f"File upload with ID {upload_id} not found.")
    
    # In a real application, you might add authorization here to ensure
    # the current_user is allowed to view this specific upload.
    # E.g., if file_upload.uploaded_by != current_user.username and current_user.role != "admin":
    #    raise AuthorizationException()

    log.info(f"Successfully retrieved upload status for ID: {upload_id}.")
    return file_upload