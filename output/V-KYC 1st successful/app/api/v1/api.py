from fastapi import APIRouter

from app.api.v1.endpoints import auth, security_tests

api_router = APIRouter()

# Include routers for different API sections
api_router.include_router(auth.router)
api_router.include_router(security_tests.router)