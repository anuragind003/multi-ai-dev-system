from fastapi import APIRouter

# Import the versioned API router
# This assumes that app/api/v1/__init__.py will define `api_v1_router`
from app.api.v1 import api_v1_router

# Create the main API router for the 'api' module
# This router will be included in the main FastAPI application (e.g., in app/main.py)
api_router = APIRouter()

# Include the version 1 API router under the /v1 prefix
# All endpoints defined in `api_v1_router` will be accessible under /api/v1/...
api_router.include_router(api_v1_router, prefix="/v1")

# Optional: Add a root endpoint for the /api path itself, e.g., for a general API status or welcome message
@api_router.get("/")
async def read_api_root():
    """
    Root endpoint for the API module.
    """
    return {"message": "Welcome to the LTFS Offer CDP API. Access v1 endpoints at /v1"}

@api_router.get("/health")
async def health_check():
    """
    Health check endpoint for the API module.
    """
    return {"status": "ok", "service": "LTFS Offer CDP API"}