from fastapi import APIRouter, status
from utils.logger import setup_logging

logger = setup_logging()

router = APIRouter()

@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    response_model=dict,
    responses={
        status.HTTP_200_OK: {"description": "API is healthy"}
    }
)
async def health_check():
    """
    Provides a simple health check endpoint for monitoring.
    Returns a status indicating the API's operational state.
    """
    logger.info("Health check endpoint accessed.")
    return {"status": "ok", "message": "V-KYC Portal API is running smoothly!"}