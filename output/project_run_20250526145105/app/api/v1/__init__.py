from fastapi import APIRouter

# Import routers from submodules within the v1 package
# These files (e.g., leads.py, admin.py, customers.py, reports.py)
# are expected to be in the same directory: app/api/v1/
from .leads import router as leads_router
from .admin import router as admin_router
from .customers import router as customers_router
from .reports import router as reports_router

# Create the main API router for version 1
v1_router = APIRouter()

# Include routers from different functional modules
# The 'prefix' argument adds a path segment before the routes defined in the included router.
# For example, a route `/` in `leads_router` will become `/leads/` under `v1_router`.
# The 'tags' argument helps organize endpoints in the OpenAPI documentation (Swagger UI).
v1_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
v1_router.include_router(customers_router, prefix="/customers", tags=["Customers"])
v1_router.include_router(reports_router, prefix="/reports", tags=["Reports"])

# This `v1_router` will then be included in the main FastAPI application instance
# (e.g., in `app/main.py`) under the `/api/v1` path.