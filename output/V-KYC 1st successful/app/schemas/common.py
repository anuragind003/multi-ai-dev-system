from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, TypeVar, Generic

# Define a generic type for the data payload
T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response format.
    """
    success: bool = Field(..., description="Indicates if the API request was successful.")
    message: str = Field(..., description="A human-readable message about the response.")
    data: Optional[T] = Field(None, description="The actual data payload of the response.")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of error details if the request failed.")

class MessageResponse(BaseModel):
    """
    Simple response model for success/failure messages without complex data.
    """
    success: bool = Field(..., description="Indicates if the operation was successful.")
    message: str = Field(..., description="A human-readable message about the operation.")

class PaginationParams(BaseModel):
    """
    Parameters for pagination in API requests.
    """
    page: int = Field(1, ge=1, description="Page number (1-indexed).")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page.")

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized paginated API response format.
    """
    success: bool = Field(..., description="Indicates if the API request was successful.")
    message: str = Field(..., description="A human-readable message about the response.")
    data: List[T] = Field(..., description="The list of items for the current page.")
    total_items: int = Field(..., description="Total number of items available.")
    total_pages: int = Field(..., description="Total number of pages available.")
    current_page: int = Field(..., description="Current page number.")
    page_size: int = Field(..., description="Number of items per page.")