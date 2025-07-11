import logging
import os
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import redis.asyncio as aioredis
from config import get_settings
from schemas import (
    UserCreate, UserResponse, UserLogin, Token,
    VKYCRecordingCreate, VKYCRecordingResponse, VKYCRecordingUpdate,
    BulkDownloadRequest, BulkDownloadStatusResponse, HealthCheckResponse
)
from models import UserRole
from services import UserService, VKYCService
from dependencies import get_db_session, get_redis_client, get_current_user, rate_limiter
from error_handling import NotFoundException, ConflictException, UnauthorizedException, ForbiddenException, BadRequestException, ServiceUnavailableException
import time
import zipfile
import io

logger = logging.getLogger("vkyc_api")
settings = get_settings()

api_router_v1 = APIRouter()

# --- Dependency for Services ---
def get_user_service(db: Session = Depends(get_db_session)) -> UserService:
    return UserService(db)

def get_vkyc_service(
    db: Session = Depends(get_db_session),
    redis_client: aioredis.Redis = Depends(get_redis_client)
) -> VKYCService:
    return VKYCService(db, redis_client)

# --- Authentication Endpoints ---
@api_router_v1.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
                    summary="Register a new user (Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.ADMIN)])
async def register_user(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Registers a new user with a specified username, password, and role.
    Only users with 'admin' role can access this endpoint.
    """
    try:
        return user_service.create_user(user_create)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user.")

@api_router_v1.post("/auth/token", response_model=Token, summary="Obtain JWT access token")
async def login_for_access_token(
    form_data: Annotated[UserLogin, Depends()],
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticates a user and returns a JWT access token.
    """
    user = user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise UnauthorizedException(
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = user_service.create_access_token(
        data={"sub": user.username, "roles": [user.role.value]}
    )
    logger.info(f"User '{user.username}' successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

@api_router_v1.get("/auth/me", response_model=UserResponse, summary="Get current user information",
                    dependencies=[Depends(rate_limiter)])
async def read_users_me(
    current_user: Annotated[UserResponse, Depends(get_current_user)]
):
    """
    Retrieves information about the currently authenticated user.
    """
    return current_user

# --- VKYC Recording Endpoints ---
@api_router_v1.post("/vkyc/recordings", response_model=VKYCRecordingResponse, status_code=status.HTTP_201_CREATED,
                    summary="Create new VKYC recording metadata (Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.PROCESS_MANAGER)])
async def create_vkyc_recording(
    recording_create: VKYCRecordingCreate,
    vkyc_service: VKYCService = Depends(get_vkyc_service)
):
    """
    Creates metadata for a new VKYC recording.
    Requires 'process_manager' or 'admin' role.
    """
    try:
        return vkyc_service.create_recording(recording_create)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Error creating VKYC recording: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create recording.")

@api_router_v1.get("/vkyc/recordings", response_model=List[VKYCRecordingResponse],
                    summary="Get all VKYC recording metadata (Team Lead/Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.TEAM_LEAD)])
async def get_all_vkyc_recordings(
    skip: int = 0,
    limit: int = 100,
    vkyc_service: VKYCService = Depends(get_vkyc_service)
):
    """
    Retrieves a list of all VKYC recording metadata.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    return vkyc_service.get_all_recordings(skip, limit)

@api_router_v1.get("/vkyc/recordings/{recording_id}", response_model=VKYCRecordingResponse,
                    summary="Get VKYC recording metadata by ID (Team Lead/Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.TEAM_LEAD)])
async def get_vkyc_recording_by_id(
    recording_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service)
):
    """
    Retrieves metadata for a specific VKYC recording by its ID.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    try:
        return vkyc_service.get_recording(recording_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)

@api_router_v1.put("/vkyc/recordings/{recording_id}", response_model=VKYCRecordingResponse,
                    summary="Update VKYC recording metadata (Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.PROCESS_MANAGER)])
async def update_vkyc_recording(
    recording_id: int,
    recording_update: VKYCRecordingUpdate,
    vkyc_service: VKYCService = Depends(get_vkyc_service)
):
    """
    Updates metadata for an existing VKYC recording.
    Requires 'process_manager' or 'admin' role.
    """
    try:
        return vkyc_service.update_recording(recording_id, recording_update)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Error updating VKYC recording {recording_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update recording.")

@api_router_v1.delete("/vkyc/recordings/{recording_id}", status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete VKYC recording metadata (Admin only)",
                      dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.ADMIN)])
async def delete_vkyc_recording(
    recording_id: int,
    vkyc_service: VKYCService = Depends(get_vkyc_service)
):
    """
    Deletes metadata for a VKYC recording.
    Requires 'admin' role.
    """
    try:
        vkyc_service.delete_recording(recording_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Error deleting VKYC recording {recording_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete recording.")

@api_router_v1.get("/vkyc/download/{lan_id}", summary="Download a single VKYC recording file (Team Lead/Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.TEAM_LEAD)])
async def download_vkyc_recording(
    lan_id: str,
    vkyc_service: VKYCService = Depends(get_vkyc_service)
):
    """
    Downloads a single VKYC recording file by its LAN ID.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    try:
        file_path = await vkyc_service.get_recording_file_path(lan_id)
        file_name = os.path.basename(file_path)
        logger.info(f"Serving file: {file_path}")
        return FileResponse(path=file_path, filename=file_name, media_type="application/octet-stream")
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ServiceUnavailableException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.detail)
    except Exception as e:
        logger.error(f"Error downloading file for LAN ID {lan_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to download file.")

@api_router_v1.post("/vkyc/bulk-download", response_model=BulkDownloadStatusResponse, status_code=status.HTTP_202_ACCEPTED,
                    summary="Initiate bulk download of VKYC recordings (Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.PROCESS_MANAGER)])
async def initiate_bulk_download(
    request: BulkDownloadRequest,
    background_tasks: BackgroundTasks,
    vkyc_service: VKYCService = Depends(get_vkyc_service)
):
    """
    Initiates a bulk download process for up to 10 VKYC recordings.
    The actual zipping and file preparation happens in a background task.
    Returns a task ID to check status.
    Requires 'process_manager' or 'admin' role.
    """
    if not request.lan_ids:
        raise BadRequestException(detail="No LAN IDs provided for bulk download.")

    task_id = await vkyc_service.initiate_bulk_download(request.lan_ids)
    
    # Add the actual processing to background tasks
    background_tasks.add_task(process_bulk_download_task, task_id, request.lan_ids, vkyc_service)
    
    logger.info(f"Bulk download task '{task_id}' initiated for LAN IDs: {request.lan_ids}")
    return BulkDownloadStatusResponse(
        task_id=task_id,
        status="PENDING",
        message="Bulk download request accepted. Check status endpoint for progress."
    )

async def process_bulk_download_task(task_id: str, lan_ids: List[str], vkyc_service: VKYCService):
    """
    Background task to process bulk download, fetch files, zip them,
    and update status in Redis.
    """
    session_key = f"bulk_download_session:{task_id}"
    temp_dir = f"/tmp/bulk_download_{task_id}"
    output_zip_path = f"{temp_dir}.zip"
    failed_lan_ids = []

    try:
        await vkyc_service.redis.hset(session_key, "status", "IN_PROGRESS")
        await vkyc_service.redis.hset(session_key, "message", "Fetching files and zipping...")
        logger.info(f"Bulk download task '{task_id}' started processing.")

        os.makedirs(temp_dir, exist_ok=True)
        
        # Create an in-memory zip file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for lan_id in lan_ids:
                try:
                    file_path = await vkyc_service.get_recording_file_path(lan_id)
                    file_name = os.path.basename(file_path)
                    zipf.write(file_path, arcname=file_name)
                    logger.debug(f"Added {file_name} to zip for task {task_id}")
                except NotFoundException:
                    logger.warning(f"File for LAN ID '{lan_id}' not found for bulk download task '{task_id}'. Skipping.")
                    failed_lan_ids.append(lan_id)
                except Exception as e:
                    logger.error(f"Error processing LAN ID '{lan_id}' for bulk download task '{task_id}': {e}")
                    failed_lan_ids.append(lan_id)
        
        # Save the zip file to a temporary location on disk
        # In a real production environment, this might be uploaded to S3 or a shared storage
        # and the download_url would point there. For this example, we'll use /tmp.
        with open(output_zip_path, "wb") as f:
            f.write(zip_buffer.getvalue())

        await vkyc_service.redis.hset(session_key, "status", "COMPLETED")
        await vkyc_service.redis.hset(session_key, "message", "Bulk download completed successfully.")
        await vkyc_service.redis.hset(session_key, "download_url", f"/api/v1/vkyc/bulk-download/{task_id}/result")
        if failed_lan_ids:
            await vkyc_service.redis.hset(session_key, "failed_lan_ids", ",".join(failed_lan_ids))
            await vkyc_service.redis.hset(session_key, "message", "Bulk download completed with some failures.")
        await vkyc_service.redis.expire(session_key, settings.REDIS_SESSION_TTL_SECONDS) # Set TTL for the session
        logger.info(f"Bulk download task '{task_id}' completed. Zip file at {output_zip_path}")

    except Exception as e:
        logger.exception(f"Bulk download task '{task_id}' failed due to an unexpected error: {e}")
        await vkyc_service.redis.hset(session_key, "status", "FAILED")
        await vkyc_service.redis.hset(session_key, "message", f"Bulk download failed: {e}")
        await vkyc_service.redis.expire(session_key, settings.REDIS_SESSION_TTL_SECONDS)
    finally:
        # Clean up temporary directory if it was created
        if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"Cleaned up temporary directory {temp_dir}")


@api_router_v1.get("/vkyc/bulk-download/{task_id}/status", response_model=BulkDownloadStatusResponse,
                    summary="Get status of a bulk download task (Team Lead/Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.TEAM_LEAD)])
async def get_bulk_download_status(
    task_id: str,
    redis_client: aioredis.Redis = Depends(get_redis_client)
):
    """
    Retrieves the current status of a bulk download task using its task ID.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    session_key = f"bulk_download_session:{task_id}"
    status_data = await redis_client.hgetall(session_key)

    if not status_data:
        raise NotFoundException(detail=f"Bulk download task '{task_id}' not found or expired.")

    status_response = BulkDownloadStatusResponse(
        task_id=task_id,
        status=status_data.get("status", "UNKNOWN"),
        message=status_data.get("message"),
        download_url=status_data.get("download_url"),
        failed_lan_ids=status_data.get("failed_lan_ids").split(",") if status_data.get("failed_lan_ids") else []
    )
    return status_response

@api_router_v1.get("/vkyc/bulk-download/{task_id}/result", summary="Download the zipped bulk recording file (Team Lead/Process Manager/Admin only)",
                    dependencies=[Depends(rate_limiter), Depends(get_current_user), Depends(UserRole.TEAM_LEAD)])
async def get_bulk_download_result(
    task_id: str,
    redis_client: aioredis.Redis = Depends(get_redis_client)
):
    """
    Downloads the zipped file for a completed bulk download task.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    session_key = f"bulk_download_session:{task_id}"
    status_data = await redis_client.hgetall(session_key)

    if not status_data:
        raise NotFoundException(detail=f"Bulk download task '{task_id}' not found or expired.")

    if status_data.get("status") != "COMPLETED":
        raise BadRequestException(detail=f"Bulk download task '{task_id}' is not yet completed. Current status: {status_data.get('status')}")

    output_zip_path = f"/tmp/bulk_download_{task_id}.zip"
    if not os.path.exists(output_zip_path):
        logger.error(f"Zip file not found for task {task_id} at {output_zip_path}")
        raise NotFoundException(detail=f"Zipped file for task '{task_id}' not found. It might have been cleaned up or failed.")

    file_name = f"vkyc_recordings_{task_id}.zip"
    logger.info(f"Serving bulk download zip file: {output_zip_path}")
    
    # Stream the file to avoid loading large files into memory
    def iterfile():
        with open(output_zip_path, mode="rb") as file_like:
            yield from file_like

    return StreamingResponse(iterfile(), media_type="application/zip", headers={
        "Content-Disposition": f"attachment; filename={file_name}",
        "X-Task-ID": task_id
    })


# --- Health Check Endpoint ---
@api_router_v1.get("/health", response_model=HealthCheckResponse, summary="Health check endpoint")
async def health_check(
    db: Session = Depends(get_db_session),
    redis_client: aioredis.Redis = Depends(get_redis_client)
):
    """
    Provides a health check for the API, database, and Redis.
    """
    db_status = "DOWN"
    redis_status = "DOWN"

    # Check DB connection
    try:
        db.execute("SELECT 1")
        db_status = "UP"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "DOWN"

    # Check Redis connection
    try:
        await redis_client.ping()
        redis_status = "UP"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "DOWN"

    # Calculate uptime (simple approximation)
    uptime_seconds = time.time() - getattr(api_router_v1, "_startup_time", time.time())
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))

    return HealthCheckResponse(
        status="UP" if db_status == "UP" and redis_status == "UP" else "DEGRADED",
        database=db_status,
        redis=redis_status,
        version=settings.APP_VERSION,
        uptime=uptime_str
    )

# Store startup time for uptime calculation
@api_router_v1.on_event("startup")
async def set_startup_time():
    api_router_v1._startup_time = time.time()