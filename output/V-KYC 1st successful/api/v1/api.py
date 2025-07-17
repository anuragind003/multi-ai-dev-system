from fastapi import APIRouter
from api.v1.endpoints import recordings, auth

api_router = APIRouter()

# Include routers for different API sections
api_router.include_router(auth.router)
api_router.include_router(recordings.router)