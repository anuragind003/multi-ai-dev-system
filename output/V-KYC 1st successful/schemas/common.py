from pydantic import BaseModel, Field

class HTTPError(BaseModel):
    """
    Standard schema for HTTP error responses.
    """
    detail: str = Field(..., example="Error message describing the issue.")

    class Config:
        schema_extra = {
            "example": {"detail": "Item not found."},
        }

class HealthCheckResponse(BaseModel):
    """
    Schema for the health check endpoint response.
    """
    status: str = Field(..., example="ok", description="Overall application status.")
    database_status: str = Field(..., example="ok", description="Database connection status.")