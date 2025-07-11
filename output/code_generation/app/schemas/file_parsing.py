from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LANIDValidationResult(BaseModel):
    """
    Schema for a single LAN ID validation result.
    """
    lan_id: str = Field(..., example="LAN1234567")
    is_valid: bool = Field(..., example=True)
    error_message: Optional[str] = Field(None, example="Invalid format")

class FileUploadResponse(BaseModel):
    """
    Schema for the response after uploading and parsing a file.
    """
    filename: str = Field(..., example="lan_ids_upload.csv")
    status: str = Field(..., example="success", description="Overall status of the file processing (success, partial_success, failed).")
    message: str = Field(..., example="File processed successfully.", description="A descriptive message about the processing result.")
    total_lan_ids: int = Field(..., example=10, description="Total number of LAN IDs found in the file.")
    valid_lan_ids_count: int = Field(..., example=8, description="Number of valid LAN IDs.")
    invalid_lan_ids_count: int = Field(..., example=2, description="Number of invalid LAN IDs.")
    validation_results: List[LANIDValidationResult] = Field(..., description="Detailed validation results for each LAN ID.")
    parsed_file_id: Optional[int] = Field(None, example=1, description="ID of the record in the database if saved.")

class ParsedFileSchema(BaseModel):
    """
    Schema for retrieving stored parsed file information.
    """
    id: int = Field(..., example=1)
    filename: str = Field(..., example="lan_ids_upload.csv")
    status: str = Field(..., example="success")
    parsed_at: datetime = Field(..., example="2023-10-27T10:00:00Z")
    lan_ids: List[str] = Field(..., example=["LAN1234567", "LAN8901234"])
    errors: Optional[List[str]] = Field(None, example=["LANInvalid: Invalid format"])

    class Config:
        from_attributes = True # For SQLAlchemy ORM compatibility