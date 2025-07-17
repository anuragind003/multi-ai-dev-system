import asyncio
import os
import time
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from config import settings
from schemas import HealthCheckResponse, HealthCheckStatus, ComponentHealth
from security import get_api_key
from utils.logger import logger

router = APIRouter()

@router.get(
    "/health",
    response_model=HealthCheckStatus,
    summary="Basic health check",
    description="Returns a simple 'OK' if the API is running.",
    status_code=status.HTTP_200_OK
)
async def basic_health_check():
    """
    Provides a basic health check endpoint to confirm the API is operational.
    Does not require authentication.
    """
    logger.debug("Basic health check requested.")
    return HealthCheckStatus(status="OK", timestamp=datetime.now())

@router.get(
    "/health/deep",
    response_model=HealthCheckResponse,
    summary="Deep health check",
    description="Performs checks on critical components like Database, NFS, and external services.",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_api_key)] # Requires API key for deep check
)
async def deep_health_check(db: AsyncSession = Depends(get_db)):
    """
    Performs a deep health check, verifying connectivity and functionality
    of critical backend components: Database, NFS, and a simulated external service.
    Requires authentication via API Key.
    """
    logger.info("Deep health check requested.")
    overall_status = "OK"
    components: list[ComponentHealth] = []

    # 1. Database Health Check
    db_status = "OK"
    db_details = None
    db_response_time = None
    try:
        start_time = time.perf_counter()
        await db.execute(text("SELECT 1"))
        end_time = time.perf_counter()
        db_response_time = int((end_time - start_time) * 1000)
        db_details = "Database connection successful."
        logger.debug("Deep health check: Database OK.")
    except Exception as e:
        db_status = "Critical"
        db_details = f"Database connection failed: {e}"
        overall_status = "Degraded"
        logger.error(f"Deep health check: Database Critical - {e}", exc_info=True)
    components.append(ComponentHealth(name="Database", status=db_status, details=db_details, response_time_ms=db_response_time))

    # 2. NFS Access Health Check (Simulated)
    nfs_status = "OK"
    nfs_details = None
    nfs_response_time = None
    try:
        start_time = time.perf_counter()
        # Simulate checking for NFS mount path existence
        if not os.path.exists(settings.NFS_MOUNT_PATH):
            raise FileNotFoundError(f"NFS mount path '{settings.NFS_MOUNT_PATH}' does not exist.")
        # Simulate a small I/O operation or just a delay
        await asyncio.sleep(0.05) # Simulate a small delay for I/O
        end_time = time.perf_counter()
        nfs_response_time = int((end_time - start_time) * 1000)
        nfs_details = f"NFS mount path '{settings.NFS_MOUNT_PATH}' accessible."
        logger.debug("Deep health check: NFS OK.")
    except FileNotFoundError as e:
        nfs_status = "Critical"
        nfs_details = f"NFS mount path not found: {e}"
        overall_status = "Degraded"
        logger.error(f"Deep health check: NFS Critical - {e}", exc_info=True)
    except Exception as e:
        nfs_status = "Error"
        nfs_details = f"NFS access failed: {e}"
        overall_status = "Degraded"
        logger.error(f"Deep health check: NFS Error - {e}", exc_info=True)
    components.append(ComponentHealth(name="NFS", status=nfs_status, details=nfs_details, response_time_ms=nfs_response_time))

    # 3. External Service Connectivity Check (Simulated Frontend-Backend dependency)
    external_service_status = "OK"
    external_service_details = None
    external_service_response_time = None
    try:
        start_time = time.perf_counter()
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.EXTERNAL_SERVICE_URL, timeout=settings.EXTERNAL_SERVICE_TIMEOUT_SECONDS)
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
        end_time = time.perf_counter()
        external_service_response_time = int((end_time - start_time) * 1000)
        external_service_details = f"External service '{settings.EXTERNAL_SERVICE_URL}' responded with status {response.status_code}."
        logger.debug("Deep health check: External Service OK.")
    except httpx.TimeoutException:
        external_service_status = "Critical"
        external_service_details = f"External service '{settings.EXTERNAL_SERVICE_URL}' timed out."
        overall_status = "Degraded"
        logger.error(f"Deep health check: External Service Critical - Timeout for {settings.EXTERNAL_SERVICE_URL}")
    except httpx.RequestError as e:
        external_service_status = "Critical"
        external_service_details = f"Network error accessing external service '{settings.EXTERNAL_SERVICE_URL}': {e}"
        overall_status = "Degraded"
        logger.error(f"Deep health check: External Service Critical - Request error for {settings.EXTERNAL_SERVICE_URL}: {e}", exc_info=True)
    except httpx.HTTPStatusError as e:
        external_service_status = "Error"
        external_service_details = f"External service '{settings.EXTERNAL_SERVICE_URL}' returned error status: {e.response.status_code} - {e.response.text}"
        overall_status = "Degraded"
        logger.error(f"Deep health check: External Service Error - HTTP status error for {settings.EXTERNAL_SERVICE_URL}: {e.response.status_code}", exc_info=True)
    except Exception as e:
        external_service_status = "Error"
        external_service_details = f"Unexpected error during external service check: {e}"
        overall_status = "Degraded"
        logger.error(f"Deep health check: External Service Error - Unexpected error for {settings.EXTERNAL_SERVICE_URL}: {e}", exc_info=True)
    components.append(ComponentHealth(name="External Service", status=external_service_status, details=external_service_details, response_time_ms=external_service_response_time))

    if overall_status == "Degraded":
        logger.warning("Deep health check completed with DEGRADED status.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=HealthCheckResponse(
                status=overall_status,
                timestamp=datetime.now(),
                components=components
            ).model_dump()
        )
    logger.info("Deep health check completed with OK status.")
    return HealthCheckResponse(status=overall_status, timestamp=datetime.now(), components=components)