# This file makes the 'endpoints' directory a Python package.
# It can also be used to import all routers for convenience in main.py.

from .user_endpoints import router as user_endpoints_router
from .recording_endpoints import router as recording_endpoints_router

# You can expose them directly if you want to import from `app.api.v1.endpoints`
# For example, in main.py: `from app.api.v1 import endpoints`
# Then `app.include_router(endpoints.user_endpoints_router)`
# Or, as done in main.py, import them directly:
# `from app.api.v1.endpoints import user_endpoints, recording_endpoints`
# and use `app.include_router(user_endpoints.router)`