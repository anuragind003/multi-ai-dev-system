python
### FILE: api_documentation.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from .config import get_settings

def custom_openapi(app: FastAPI):
    """
    Generates custom OpenAPI schema.
    """
    if app.openapi_schema:
        return app.openapi_schema

    settings = get_settings()
    openapi_schema = get_openapi(
        title=settings.app_name,
        version="1.0.0",
        description="API for managing tasks.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def configure_api_documentation(app: FastAPI):
    """
    Configures API documentation.
    """
    app.openapi = custom_openapi