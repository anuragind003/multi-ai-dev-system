from datetime import datetime
from typing import List, Optional, TypeVar, Generic
from uuid import UUID

from pydantic import BaseModel, Field
from enum import Enum

# Define a TypeVar for generic pagination
T = TypeVar("T")

# --- Enums ---

class OfferStatus(str, Enum):
    """
    Represents the status of an offer.
    (FR18, FR20, FR51, FR53)
    """
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    EXPIRED = "Expired"
    DUPLICATE = "Duplicate"
    JOURNEY_STARTED = "Journey Started" # Implied by FR15, FR21, FR25, FR26, FR53

class OfferType(str, Enum):
    """
    Represents the type of an offer for campaigning.
    (FR19)
    """
    FRESH = "Fresh"
    ENRICH = "Enrich"
    NEW_OLD = "New-old"
    NEW_NEW = "New-new"

class ProductType(str, Enum):
    """
    Represents the type of loan product.
    (FR4, FR28, FR29, FR30, FR31, FR32, FR43)
    """
    LOYALTY = "Loyalty"
    PREAPPROVED = "Preapproved"
    E_AGGREGATOR = "E-aggregator"
    INSTA = "Insta"
    TOP_UP = "Top-up"
    EMPLOYEE_LOAN = "Employee Loan"
    PROSPECT = "Prospect"
    TWL = "TWL" # Two-Wheeler Loan, implied by TW-L Product in FR19 and TWL in FR28

class EventSource(str, Enum):
    """
    Represents the source system of an event.
    (FR33)
    """
    MOENGAGE = "Moengage"
    LOS = "LOS"

class EventType(str, Enum):
    """
    Represents the type of event tracked.
    (FR33)
    """
    SMS_SENT = "SMS_SENT"
    SMS_DELIVERED = "SMS_DELIVERED"
    CLICK = "CLICK"
    CONVERSION = "CONVERSION"
    LOGIN = "LOGIN"
    BUREAU_CHECK = "BUREAU_CHECK"
    OFFER_DETAILS_VIEWED = "OFFER_DETAILS_VIEWED"
    EKYC_COMPLETED = "EKYC_COMPLETED"
    BANK_DETAILS_ENTERED = "BANK_DETAILS_ENTERED"
    OTHER_DETAILS_FILLED = "OTHER_DETAILS_FILLED"
    E_SIGN_COMPLETED = "E_SIGN_COMPLETED"
    APPLICATION_EXPIRED = "APPLICATION_EXPIRED" # Implied by FR15, FR16
    APPLICATION_REJECTED = "APPLICATION_REJECTED" # Implied by FR15, FR16


# --- Base Schemas ---

class TimestampedSchema(BaseModel):
    """
    Base schema for models that include creation and update timestamps.
    """
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True # For Pydantic v2, equivalent to orm_mode = True in v1

class UUIDSchema(BaseModel):
    """
    Base schema for models that have a UUID as their primary identifier.
    """
    id: UUID

    class Config:
        from_attributes = True

# --- Common API Responses ---

class SuccessResponse(BaseModel):
    """
    Generic success response schema.
    """
    status: str = "success"
    message: str = "Operation successful"
    detail: Optional[dict] = None

class ErrorResponse(BaseModel):
    """
    Generic error response schema.
    """
    status: str = "error"
    message: str = "An error occurred"
    error_code: Optional[str] = None
    detail: Optional[dict] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic schema for paginated list responses.
    """
    total: int = Field(..., description="Total number of items available")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    items: List[T] = Field(..., description="List of items for the current page")

    class Config:
        from_attributes = True

# --- Common Data Schemas ---

class CustomerIdentifiers(BaseModel):
    """
    Schema for common customer identifiers used for deduplication and lookup.
    (FR3, FR5, FR8)
    """
    mobile_number: Optional[str] = Field(None, max_length=20, pattern=r"^\d{10}$", description="Customer's 10-digit mobile number")
    pan_number: Optional[str] = Field(None, max_length=10, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", description="Customer's PAN number")
    aadhaar_ref_number: Optional[str] = Field(None, max_length=12, pattern=r"^\d{12}$", description="Customer's Aadhaar reference number")
    ucid_number: Optional[str] = Field(None, max_length=50, description="Customer's Unique Customer ID (UCID)")
    previous_loan_application_number: Optional[str] = Field(None, max_length=50, description="Previous loan application number")

    class Config:
        from_attributes = True