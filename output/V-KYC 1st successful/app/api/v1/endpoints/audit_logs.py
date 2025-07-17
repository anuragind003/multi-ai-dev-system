### FILE: app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.endpoints import audit_logs
from app.api.v1.endpoints import auth # Assuming an auth endpoint for token generation

api_router = APIRouter()

# Include routers for different API functionalities
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
# Add an authentication endpoint for users to get JWT tokens
# This would typically be in a separate file like app/api/v1/endpoints/auth.py
# For this example, I'll provide a minimal auth endpoint directly here or in a new file.
# Let's create a new file for auth for better structure.
api_router.include_router(auth.router, tags=["Authentication"])