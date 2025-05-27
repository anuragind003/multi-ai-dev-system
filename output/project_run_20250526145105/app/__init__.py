from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import application settings and database utilities
# These modules are assumed to exist in the 'app/core' directory
from app.core.config import settings
from app.core.database import engine, Base # Base and engine are imported for potential future use or clarity,
                                           # though table creation is typically handled by migrations.

# Import API routers from the 'app/api/v1/endpoints' directory
# Each router groups related API endpoints
from app.api.v1.endpoints import leads, admin, customers, reports

# Define an asynchronous context manager for application lifespan events.
# This allows for executing code during application startup and shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    During startup, it can perform initializations like database connection checks.
    During shutdown, it can perform cleanup operations.
    """
    print("Application startup: Initializing LTFS Offer CDP services...")
    # In a production environment, database table creation should be handled
    # by a dedicated migration tool (e.g., Alembic) and not directly here.
    # For development/testing, one might uncomment:
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    yield  # The application will run while this context is active
    print("Application shutdown: Cleaning up resources...")
    # Any cleanup logic can go here, e.g., closing external connections.

# Initialize the FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",  # OpenAPI documentation UI
    redoc_url="/redoc", # ReDoc documentation UI
    lifespan=lifespan, # Attach the defined lifespan context manager
)

# Configure Cross-Origin Resource Sharing (CORS) middleware.
# This is essential for allowing the Vue.js frontend to make requests to the FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS], # Allowed origins from settings
    allow_credentials=True,  # Allow cookies to be included in cross-origin HTTP requests
    allow_methods=["*"],     # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],     # Allow all HTTP headers
)

# Include API routers into the main FastAPI application.
# Each router is prefixed with the API version string (e.g., "/api/v1")
# and tagged for better organization in the OpenAPI documentation.
app.include_router(leads.router, prefix=settings.API_V1_STR, tags=["Leads"])
app.include_router(admin.router, prefix=settings.API_V1_STR, tags=["Admin"])
app.include_router(customers.router, prefix=settings.API_V1_STR, tags=["Customers"])
app.include_router(reports.router, prefix=settings.API_V1_STR, tags=["Reports"])

# Define a simple root endpoint for health checks or basic information.
@app.get("/")
async def root():
    """
    Root endpoint of the API. Returns a simple message to indicate the API is running.
    """
    return {"message": "LTFS Offer CDP API is running successfully!"}