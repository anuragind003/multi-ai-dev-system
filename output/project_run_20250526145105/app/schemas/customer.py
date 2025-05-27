import uuid
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, model_validator, ValidationError

# Enums based on BRD analysis and common loan product types
class OfferStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    EXPIRED = "Expired"
    DUPLICATE = "Duplicate"

class OfferType(str, Enum):
    FRESH = "Fresh"
    ENRICH = "Enrich"
    NEW_OLD = "New-old"
    NEW_NEW = "New-new"

class ProductType(str, Enum):
    LOYALTY = "Loyalty"
    PREAPPROVED = "Preapproved"
    E_AGGREGATOR = "E-aggregator"
    INSTA = "Insta"
    TOP_UP = "Top-up"
    EMPLOYEE_LOAN = "Employee Loan"
    PROSPECT = "Prospect"
    TW_L = "TW-L" # Two-Wheeler Loan, derived from FR19

class EventSource(str, Enum):
    MOENGAGE = "Moengage"
    LOS = "LOS"

class EventType(str, Enum):
    SMS_SENT = "SMS_SENT"
    DELIVERED = "DELIVERED"
    CLICK = "CLICK"
    CONVERSION = "CONVERSION"
    LOGIN = "LOGIN"
    BUREAU_CHECK = "BUREAU_CHECK"
    OFFER_DETAILS = "OFFER_DETAILS"
    EKYC = "EKYC"
    BANK_DETAILS = "BANK_DETAILS"
    OTHER_DETAILS = "OTHER_DETAILS"
    E_SIGN = "E_SIGN"

# --- Customer Schemas ---
class CustomerBase(BaseModel):
    mobile_number: Optional[str] = Field(None, max_length=20, pattern=r"^\d{10}$", description="10-digit mobile number")
    pan_number: Optional[str] = Field(None, max_length=10, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", description="10-character PAN number (e.g., ABCDE1234F)")
    aadhaar_ref_number: Optional[str] = Field(None, max_length=12, pattern=r"^\d{12}$", description="12-digit Aadhaar reference number")
    ucid_number: Optional[str] = Field(None, max_length=50, description="Unique Customer ID from external systems")
    previous_loan_app_number: Optional[str] = Field(None, max_length=50, description="Reference to a previous loan application number")
    customer_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Flexible storage for various customer attributes (JSONB)")
    customer_segments: Optional[List[str]] = Field(default_factory=list, description="List of customer segments (e.g., C1, C2)")
    propensity_flag: Optional[str] = Field(None, max_length=50, description="Analytics-defined flag for customer propensity")
    dnd_status: Optional[bool] = Field(False, description="Do Not Disturb status for the customer")

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode for Pydantic v2

class CustomerCreate(CustomerBase):
    """Schema for creating a new customer. Identifiers are optional here,
    but business logic will enforce at least one for deduplication."""
    pass

class CustomerUpdate(CustomerBase):
    """Schema for updating an existing customer. All fields are optional."""
    pass

class CustomerResponse(CustomerBase):
    """Schema for returning customer data in API responses."""
    customer_id: uuid.UUID = Field(..., description="Unique identifier for the customer")
    created_at: datetime = Field(..., description="Timestamp when the customer record was created")
    updated_at: datetime = Field(..., description="Timestamp when the customer record was last updated")

# --- Offer Schemas ---
class OfferBase(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Foreign key to the customer table")
    offer_type: OfferType = Field(..., description="Type of offer (e.g., Fresh, Enrich)")
    offer_status: OfferStatus = Field(..., description="Current status of the offer (e.g., Active, Expired)")
    product_type: ProductType = Field(..., description="Loan product type for the offer (e.g., Loyalty, Top-up)")
    offer_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Flexible storage for offer-specific data (JSONB)")
    offer_start_date: Optional[date] = Field(None, description="Date when the offer becomes active")
    offer_end_date: Optional[date] = Field(None, description="Date when the offer expires")
    is_journey_started: Optional[bool] = Field(False, description="Flag indicating if a loan application journey has started for this offer")
    loan_application_id: Optional[str] = Field(None, max_length=50, description="ID of the loan application if journey started")

    model_config = ConfigDict(from_attributes=True)

class OfferCreate(OfferBase):
    """Schema for creating a new offer. Customer ID is required as it links to an existing customer."""
    pass

class OfferUpdate(OfferBase):
    """Schema for updating an existing offer. All fields are optional for updates."""
    customer_id: Optional[uuid.UUID] = None # Customer ID should not be updated via offer update
    offer_type: Optional[OfferType] = None
    offer_status: Optional[OfferStatus] = None
    product_type: Optional[ProductType] = None
    # Other fields are already Optional in OfferBase

class OfferResponse(OfferBase):
    """Schema for returning offer data in API responses."""
    offer_id: uuid.UUID = Field(..., description="Unique identifier for the offer")
    created_at: datetime = Field(..., description="Timestamp when the offer record was created")
    updated_at: datetime = Field(..., description="Timestamp when the offer record was last updated")

# --- Offer History Schemas ---
class OfferHistoryBase(BaseModel):
    offer_id: uuid.UUID = Field(..., description="Foreign key to the offer table")
    customer_id: uuid.UUID = Field(..., description="Foreign key to the customer table")
    change_timestamp: datetime = Field(..., description="Timestamp of the history record")
    old_offer_status: OfferStatus = Field(..., description="Offer status before the change")
    new_offer_status: OfferStatus = Field(..., description="Offer status after the change")
    change_reason: Optional[str] = Field(None, description="Reason for the offer status change")
    snapshot_offer_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Snapshot of offer details at the time of change (JSONB)")

    model_config = ConfigDict(from_attributes=True)

class OfferHistoryResponse(OfferHistoryBase):
    """Schema for returning offer history data in API responses."""
    history_id: uuid.UUID = Field(..., description="Unique identifier for the offer history record")

# --- Campaign Event Schemas ---
class CampaignEventBase(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Foreign key to the customer table")
    offer_id: Optional[uuid.UUID] = Field(None, description="Optional foreign key to the offer table, if event is tied to a specific offer")
    event_source: EventSource = Field(..., description="Source of the event (e.g., Moengage, LOS)")
    event_type: EventType = Field(..., description="Type of event (e.g., SMS_SENT, CONVERSION)")
    event_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw event data (JSONB)")
    event_timestamp: datetime = Field(..., description="Timestamp when the event occurred")

    model_config = ConfigDict(from_attributes=True)

class CampaignEventCreate(CampaignEventBase):
    """Schema for creating a new campaign event. Event timestamp can be optional for creation,
    as it might be set by the server."""
    event_timestamp: Optional[datetime] = None

class CampaignEventResponse(CampaignEventBase):
    """Schema for returning campaign event data in API responses."""
    event_id: uuid.UUID = Field(..., description="Unique identifier for the campaign event")

# --- Combined Response Schemas for specific API endpoints ---
class CustomerWithOffersResponse(CustomerResponse):
    """
    Schema for retrieving a single profile view of a customer,
    including their current offers and a summary of offer history.
    Corresponds to GET /api/v1/customers/{customer_id}
    """
    current_offer: Optional[OfferResponse] = Field(None, description="The customer's current active offer")
    offer_history_summary: List[OfferResponse] = Field(default_factory=list, description="A summary list of past offers for the customer")
    journey_status: Optional[str] = Field(None, description="Current status of the customer's loan application journey (derived)")

# Schema for the /api/v1/leads POST request body
class LeadCreateRequest(BaseModel):
    mobile_number: Optional[str] = Field(None, max_length=20, pattern=r"^\d{10}$", description="Customer's mobile number")
    pan_number: Optional[str] = Field(None, max_length=10, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", description="Customer's PAN number")
    aadhaar_ref_number: Optional[str] = Field(None, max_length=12, pattern=r"^\d{12}$", description="Customer's Aadhaar reference number")
    loan_product: ProductType = Field(..., description="The product type for the offer associated with this lead")
    offer_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Specific details of the offer for this lead")

    @model_validator(mode='after')
    def validate_identifiers(self) -> 'LeadCreateRequest':
        """Ensures at least one primary identifier is provided for a lead."""
        if not any([self.mobile_number, self.pan_number, self.aadhaar_ref_number]):
            raise ValueError("At least one identifier (mobile_number, pan_number, or aadhaar_ref_number) must be provided.")
        return self

# Schema for a single row in the /api/v1/admin/customer_offers/upload file content
class AdminCustomerOfferUploadRow(BaseModel):
    """
    Schema representing a single row of data expected in the customer offer upload file.
    Combines customer identifiers, attributes, and offer details.
    """
    # Customer Identifiers (at least one required for deduplication)
    mobile_number: Optional[str] = Field(None, max_length=20, pattern=r"^\d{10}$", description="Customer's mobile number")
    pan_number: Optional[str] = Field(None, max_length=10, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", description="Customer's PAN number")
    aadhaar_ref_number: Optional[str] = Field(None, max_length=12, pattern=r"^\d{12}$", description="Customer's Aadhaar reference number")
    ucid_number: Optional[str] = Field(None, max_length=50, description="Unique Customer ID from external systems")
    previous_loan_app_number: Optional[str] = Field(None, max_length=50, description="Reference to a previous loan application number")

    # Customer Attributes (optional)
    customer_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Flexible storage for various customer attributes (JSONB)")
    customer_segments: Optional[List[str]] = Field(default_factory=list, description="List of customer segments (e.g., C1, C2)")
    propensity_flag: Optional[str] = Field(None, max_length=50, description="Analytics-defined flag for customer propensity")
    dnd_status: Optional[bool] = Field(False, description="Do Not Disturb status for the customer")

    # Offer Details (required for an offer upload)
    offer_type: OfferType = Field(..., description="Type of offer (e.g., Fresh, Enrich)")
    product_type: ProductType = Field(..., description="Loan product type for the offer (e.g., Loyalty, Top-up)")
    offer_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Specific details of the offer (JSONB)")
    offer_start_date: Optional[date] = Field(None, description="Date when the offer becomes active")
    offer_end_date: Optional[date] = Field(None, description="Date when the offer expires")

    @model_validator(mode='after')
    def validate_identifiers(self) -> 'AdminCustomerOfferUploadRow':
        """Ensures at least one primary identifier is provided for each row in the upload."""
        if not any([self.mobile_number, self.pan_number, self.aadhaar_ref_number, self.ucid_number, self.previous_loan_app_number]):
            raise ValueError("At least one identifier (mobile_number, pan_number, aadhaar_ref_number, ucid_number, or previous_loan_app_number) must be provided for each row.")
        return self

# Schemas for file upload results and summary
class UploadResultRow(BaseModel):
    """Represents the processing result for a single row from an uploaded file."""
    row_number: int = Field(..., description="The original row number from the uploaded file")
    status: str = Field(..., description="Processing status: 'Success' or 'Failed'")
    customer_id: Optional[uuid.UUID] = Field(None, description="ID of the created/updated customer, if successful")
    offer_id: Optional[uuid.UUID] = Field(None, description="ID of the created/updated offer, if successful")
    error_description: Optional[str] = Field(None, description="Description of the error, if processing failed")

class UploadSummaryResponse(BaseModel):
    """Provides a summary of a bulk upload operation."""
    total_rows: int = Field(..., description="Total number of rows processed")
    successful_rows: int = Field(..., description="Number of rows processed successfully")
    failed_rows: int = Field(..., description="Number of rows that failed processing")
    job_id: uuid.UUID = Field(..., description="Unique identifier for the upload job")
    # In a real API, this might also include URLs to download success/error files.

# Schema for daily reports (FR49)
class DailyReportResponse(BaseModel):
    """Schema for daily data tally reports."""
    report_date: date = Field(..., description="Date for which the report is generated")
    total_customers: int = Field(..., description="Total unique customers in the CDP")
    active_offers: int = Field(..., description="Total active offers in the CDP")
    new_leads_today: int = Field(..., description="Number of new leads processed today")
    conversions_today: int = Field(..., description="Number of conversions recorded today")
    campaigns_attempted_today: Optional[int] = Field(None, description="Number of campaigns attempted today")
    campaigns_successfully_sent_today: Optional[int] = Field(None, description="Number of campaigns successfully sent today")
    campaigns_failed_today: Optional[int] = Field(None, description="Number of campaigns that failed today")
    campaign_success_rate_today: Optional[float] = Field(None, description="Success rate of campaigns today (0.0-1.0)")
    campaign_conversion_rate_today: Optional[float] = Field(None, description="Conversion rate of campaigns today (0.0-1.0)")

    model_config = ConfigDict(from_attributes=True)