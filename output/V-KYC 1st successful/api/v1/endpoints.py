import logging
import csv
import io
import base64
from typing import List, Tuple
from fastapi import APIRouter, Depends, status, Response, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import (
    UserCreate, UserResponse, Token, UserLogin,
    VKYCRecordCreate, VKYCRecordResponse, VKYCSearchParams, VKYCRecordUpdate,
    BulkUploadRequest, BulkUploadResponse, HealthCheckResponse
)
from services import UserService, VKYCService
from utils.security import create_access_token, get_current_user
from models import User, UserRole
from exceptions import APIException, NotFoundException, ForbiddenException, InvalidInputException
from config import settings

logger = logging.getLogger(__name__)

# --- Dependency Injection for Services ---
async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)

async def get_vkyc_service(db: AsyncSession = Depends(get_db)) -> VKYCService:
    return VKYCService(db)

# --- Routers ---
auth_router = APIRouter()
vkyc_router = APIRouter()
health_router = APIRouter()

# --- Authentication Endpoints ---
@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user) # Only admin can register new users
):
    """
    Registers a new user. Only users with 'admin' role can register new users.
    """
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Only administrators can register new users.")
    logger.info(f"Admin user {current_user.username} attempting to register new user: {user_data.username}")
    return await user_service.create_user(user_data)

@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticates a user and returns an access token.
    """
    user = await user_service.authenticate_user(UserLogin(username=form_data.username, password=form_data.password))
    access_token = create_access_token(
        data={"sub": user.username, "scopes": [user.role.value]}
    )
    logger.info(f"User {user.username} successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Retrieves the current authenticated user's information.
    """
    return current_user

# --- VKYC Records Endpoints ---
@vkyc_router.post("/", response_model=VKYCRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_vkyc_record(
    record_data: VKYCRecordCreate,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new VKYC record. Requires authentication.
    """
    logger.info(f"User {current_user.username} attempting to create VKYC record for LAN ID: {record_data.lan_id}")
    return await vkyc_service.create_record(record_data, current_user.id)

@vkyc_router.get("/{record_id}", response_model=VKYCRecordResponse)
async def get_vkyc_record(
    record_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a VKYC record by ID. Requires authentication.
    Users can only view records they uploaded, unless they are Admin or Process Manager.
    """
    record = await vkyc_service.get_record_by_id(record_id)
    if current_user.role not in [UserRole.ADMIN, UserRole.PROCESS_MANAGER] and record.uploaded_by != current_user.id:
        raise ForbiddenException("You do not have permission to view this record.")
    return record

@vkyc_router.get("/", response_model=List[VKYCRecordResponse])
async def search_vkyc_records(
    params: VKYCSearchParams = Depends(),
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: User = Depends(get_current_user)
):
    """
    Searches VKYC records based on various criteria. Requires authentication.
    Team Leads can only search their own uploaded records.
    Admins and Process Managers can search all records.
    """
    if current_user.role == UserRole.TEAM_LEAD:
        if params.uploaded_by is not None and params.uploaded_by != current_user.id:
            raise ForbiddenException("Team Leads can only search their own uploaded records.")
        params.uploaded_by = current_user.id # Force filter by current user's ID

    records, total_count = await vkyc_service.search_records(params)
    # Add custom header for total count for pagination on frontend
    return Response(
        content=VKYCRecordResponse.model_validate(records).model_dump_json(by_alias=True),
        media_type="application/json",
        headers={"X-Total-Count": str(total_count)}
    )

@vkyc_router.put("/{record_id}", response_model=VKYCRecordResponse)
async def update_vkyc_record(
    record_id: int,
    update_data: VKYCRecordUpdate,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: User = Depends(get_current_user)
):
    """
    Updates an existing VKYC record. Only Admin or Process Manager can update.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.PROCESS_MANAGER]:
        raise ForbiddenException("Only administrators or process managers can update records.")
    logger.info(f"User {current_user.username} attempting to update VKYC record ID: {record_id}")
    return await vkyc_service.update_record(record_id, update_data)

@vkyc_router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vkyc_record(
    record_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a VKYC record. Only Admin can delete.
    """
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Only administrators can delete records.")
    logger.info(f"Admin user {current_user.username} attempting to delete VKYC record ID: {record_id}")
    await vkyc_service.delete_record(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@vkyc_router.post("/bulk-upload", response_model=BulkUploadResponse, status_code=status.HTTP_200_OK)
async def bulk_upload_vkyc_records(
    bulk_request: BulkUploadRequest,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads VKYC record metadata in bulk from a CSV/TXT file.
    Requires 'admin' or 'process_manager' role.
    The file content should be base64 encoded.
    Expected CSV format: lan_id,customer_name,recording_date(ISO 8601),file_path,file_size_bytes,status,notes
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.PROCESS_MANAGER]:
        raise ForbiddenException("Only administrators or process managers can perform bulk uploads.")

    try:
        decoded_content = base64.b64decode(bulk_request.file_content).decode('utf-8')
        csv_file = io.StringIO(decoded_content)
        reader = csv.DictReader(csv_file)

        records_to_create: List[VKYCRecordCreate] = []
        parsing_errors = []

        for i, row in enumerate(reader):
            try:
                # Basic validation and type conversion for CSV rows
                record_data = {
                    "lan_id": row["lan_id"].strip(),
                    "customer_name": row["customer_name"].strip(),
                    "recording_date": datetime.fromisoformat(row["recording_date"].strip().replace('Z', '+00:00')),
                    "file_path": row["file_path"].strip(),
                    "file_size_bytes": int(row["file_size_bytes"].strip()) if row.get("file_size_bytes") else None,
                    "status": VKYCRecordStatus(row["status"].strip().lower()) if row.get("status") else VKYCRecordStatus.PENDING,
                    "notes": row.get("notes", "").strip()
                }
                records_to_create.append(VKYCRecordCreate(**record_data))
            except KeyError as e:
                parsing_errors.append({
                    "row_index": i + 1,
                    "error": f"Missing required column: {e}",
                    "data": row
                })
                logger.warning(f"Bulk upload parsing error at row {i+1}: Missing column {e}")
            except ValueError as e:
                parsing_errors.append({
                    "row_index": i + 1,
                    "error": f"Data type or format error: {e}",
                    "data": row
                })
                logger.warning(f"Bulk upload parsing error at row {i+1}: Data format error {e}")
            except Exception as e:
                parsing_errors.append({
                    "row_index": i + 1,
                    "error": f"Unexpected parsing error: {e}",
                    "data": row
                })
                logger.error(f"Bulk upload unexpected parsing error at row {i+1}: {e}", exc_info=True)

        if parsing_errors:
            # If there are parsing errors, we might want to stop or continue with valid ones.
            # For now, we'll proceed with valid ones and report parsing errors.
            logger.warning(f"Bulk upload: {len(parsing_errors)} parsing errors found.")

        successful, failed, db_errors = await vkyc_service.bulk_upload_records(records_to_create, current_user.id)

        return BulkUploadResponse(
            total_records=len(records_to_create) + len(parsing_errors), # Total attempted
            successful_records=successful,
            failed_records=failed + len(parsing_errors), # Include parsing errors in failed count
            errors=parsing_errors + db_errors
        )

    except UnicodeDecodeError:
        raise InvalidInputException("File content is not valid UTF-8. Ensure it's a plain text CSV/TXT.")
    except Exception as e:
        logger.error(f"Error during bulk upload: {e}", exc_info=True)
        raise APIException(f"Failed to process bulk upload: {e}")

@vkyc_router.get("/{record_id}/download", response_class=FileResponse)
async def download_vkyc_record(
    record_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service),
    current_user: User = Depends(get_current_user)
):
    """
    Downloads a VKYC recording file. Requires authentication.
    Only Admin or the user who uploaded the record can download.
    This endpoint simulates file serving from an NFS path.
    """
    # In a real scenario, this would stream the file directly from the NFS path
    # using a library like aiofiles. For demonstration, we'll return a dummy file.
    # The actual file path would be retrieved from the record.
    try:
        file_path = await vkyc_service.get_file_stream(record_id, current_user)
        # Simulate a file existing at the path. In production, ensure this path is accessible.
        # For testing, you might create a dummy file or mock the file system.
        # Here, we'll return a dummy text file.
        dummy_file_path = "dummy_vkyc_recording.txt"
        with open(dummy_file_path, "w") as f:
            f.write(f"This is a dummy VKYC recording for LAN ID {record_id}.\n")
            f.write(f"Original path: {file_path}\n")
            f.write("In a real system, this would be the actual video/audio content.\n")

        logger.info(f"Serving dummy file for record ID {record_id}.")
        return FileResponse(
            path=dummy_file_path,
            filename=f"vkyc_recording_{record_id}.txt",
            media_type="text/plain" # Change to appropriate media type (e.g., video/mp4)
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    except Exception as e:
        logger.error(f"Error downloading record ID {record_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to download file.")


# --- Health Check Endpoint ---
@health_router.get("/", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Provides a health check endpoint for monitoring.
    Checks database connectivity.
    """
    db_status = "disconnected"
    try:
        # Attempt a simple query to check DB connection
        await db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        db_status = f"failed: {e}"

    return HealthCheckResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database_status=db_status,
        version=settings.API_VERSION,
        timestamp=datetime.now()
    )