from fastapi import APIRouter

from app.api.v1.routers import auth, health

api_router = APIRouter()

# Include individual routers for different API functionalities
api_router.include_router(auth.router)
api_router.include_router(health.router)

# You can add more routers here as your application grows, e.g.:
# from app.api.v1.routers import user_management, recordings
# api_router.include_router(user_management.router)
# api_router.include_router(recordings.router)