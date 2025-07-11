from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from utils.logger import logger

router = APIRouter()

@router.get(
    "/",
    summary="Basic health check",
    response_description="Returns status 'ok' if the service is running."
)
async def health_check():
    """
    Provides a basic health check endpoint to indicate if the application is running.
    """
    logger.debug("Health check endpoint hit.")
    return JSONResponse(content={"status": "ok"})

@router.get(
    "/db",
    summary="Database health check",
    response_description="Returns status 'ok' if the database connection is active.",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Database connection failed."}
    }
)
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """
    Checks the database connection by executing a simple query.
    """
    logger.debug("Database health check endpoint hit.")
    try:
        # Execute a simple query to check the connection
        await db.execute(text("SELECT 1"))
        logger.info("Database connection is healthy.")
        return JSONResponse(content={"status": "ok", "database": "connected"})
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "database": "disconnected", "detail": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )