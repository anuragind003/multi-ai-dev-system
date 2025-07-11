python
### FILE: health_check.py
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import logging

# Configure logging
logger = logging.getLogger(__name__)

def configure_health_check(app: FastAPI):
    """
    Configures health check endpoints.
    """
    @app.get("/health", status_code=status.HTTP_200_OK, tags=["health"])
    async def health_check():
        """
        Health check endpoint.
        """
        try:
            # Add database connection check here if needed
            return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)