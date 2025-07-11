from fastapi import APIRouter
from core.config import settings
from api.v1.endpoints import auth, tests

# Main API router for version 1
api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include test management endpoints
api_router.include_router(tests.router, prefix="/tests", tags=["Test Cases & Test Runs"])

# You can add more routers here as your API grows
# For example:
# from api.v1.endpoints import reports
# api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])