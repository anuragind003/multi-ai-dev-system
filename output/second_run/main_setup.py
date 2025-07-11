from fastapi import FastAPI
from .config import settings
from .error_handling import configure_error_handlers
from .security import configure_cors, configure_security_headers, configure_rate_limiting
from .health_check import configure_health_check
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    """
    app = FastAPI(
        title="Task Management API",
        description="API for managing tasks",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        openapi_tags=[
            {"name": "tasks", "description": "Operations related to tasks."},
            {"name": "auth", "description": "Authentication and authorization."},
        ],
    )

    # Configure CORS
    configure_cors(app)

    # Configure security headers
    configure_security_headers(app)

    # Configure rate limiting
    configure_rate_limiting(app)

    # Configure error handlers
    configure_error_handlers(app)

    # Configure health check
    configure_health_check(app)

    # Import and include routers (assuming you have a routers directory)
    from .routers import tasks, auth
    app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])

    return app