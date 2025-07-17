import logging
from fastapi import APIRouter

from app.api.v1.endpoints import file_upload

logger = logging.getLogger(__name__)

api_router = APIRouter()

# Include routers for different API functionalities
api_router.include_router(file_upload.router, prefix="/files", tags=["Files"])

# You can add more routers here for other functionalities like user management, etc.
# api_router.include_router(user_endpoints.router, prefix="/users", tags=["Users"])

logger.info("API v1 routers initialized.")