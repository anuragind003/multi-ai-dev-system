python
### FILE: dependency_injection.py
from fastapi import FastAPI
from .config import get_settings
from .database import get_db
from .error_handling import configure_error_handlers
from .security_middleware import configure_security_middleware
from .api_documentation import configure_api_documentation
from .health_check import configure_health_check
import logging

# Configure logging
logger = logging.getLogger(__name__)

def configure_dependencies(app: FastAPI):
    """
    Configures dependencies for the FastAPI application.
    """
    # Error handling
    configure_error_handlers(app)

    # Security Middleware
    configure_security_middleware(app)

    # API Documentation
    configure_api_documentation(app)

    # Health Check
    configure_health_check(app)

    # Example of dependency injection using settings
    @app.get("/api/v1/example")
    async def example_route(settings = get_settings()):
        """
        Example route demonstrating dependency injection.
        """
        logger.info("Example route accessed")
        return {"message": f"Hello from {settings.app_name}!"}