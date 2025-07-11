from fastapi import APIRouter

from app.api.v1.endpoints import auth, vkyc_recordings

# Main API router for version 1
api_router = APIRouter()

# Include specific routers
api_router.include_router(auth.router)
api_router.include_router(vkyc_recordings.router)