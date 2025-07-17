import logging
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi_limiter.depends import RateLimiter

from app.core.dependencies import get_file_parser_service, get_current_user
from app.core.config import settings
from app.schemas.file_parsing import FileUploadResponse
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/upload-lan-ids",
    response_model=FileUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload LAN IDs File",
    description="Uploads a CSV or TXT file containing LAN IDs for parsing and validation. "
                "Each LAN ID should be on a new line. "
                f"The file must contain between {get_file_parser_service.__wrapped__.MIN_LAN_IDS} "
                f"and {get_file_parser_service.__wrapped__.MAX_LAN_IDS} LAN IDs. "
                "LAN IDs must follow the format 'LAN' followed by 7 digits (e.g., LAN1234567).",
    responses={
        status.HTTP_200_OK: {"model": FileUploadResponse, "description": "File processed successfully."},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid file content or LAN ID count."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not authorized."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse, "description": "Validation error for request parameters."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error during file processing or database operation."},
    },
    tags=["File Upload"],
    dependencies=[
        Depends(RateLimiter(times=int(settings.RATE_LIMIT_PER_MINUTE.split('/')[0]),
                            minutes=1 if 'minute' in settings.RATE_LIMIT_PER_MINUTE else 0,
                            seconds=1 if 'second' in settings.RATE_LIMIT_PER_MINUTE else 0)),
        # Depends(get_current_user) # Uncomment to enable authentication for this endpoint
    ]
)
async def upload_lan_ids_file(
    file: Annotated[UploadFile, File(description="CSV or TXT file containing LAN IDs.")],
    file_parser_service: Annotated[FileParserService, Depends(get_file_parser_service)],
):
    """
    Handles the upload of a file containing LAN IDs.
    The file is parsed, each LAN ID is validated against a specific format and count constraints.
    Results are stored in the database and returned to the user.
    """
    logger.info(f"Received file upload request for: {file.filename}")
    result = await file_parser_service.parse_and_validate_file(file)
    logger.info(f"File '{file.filename}' processed. Status: {result['status']}")
    return result