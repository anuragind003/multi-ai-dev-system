import uuid
from datetime import date, datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, ConfigDict, model_validator

# Base schema for Offer, containing common fields for request bodies
class OfferBase(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Unique identifier for the customer")
    offer_type: str = Field(..., description="Type of offer, e.g., 'Fresh', 'Enrich', 'New-old', 'New-new'")
    offer_status: str = Field(..., description="Current status of the offer, e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'")
    product_type: str = Field(..., description="Product associated with the offer, e.g., 'Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan'")
    offer_details: Dict[str, Any] = Field(default_factory=dict, description="Flexible JSON storage for offer specific data")
    offer_start_date: date = Field(..., description="Date when the offer becomes active")
    offer_end_date: date = Field(..., description="Date when the offer expires")
    is_journey_started: bool = Field(default=False, description="Flag indicating if a loan application journey has started for this offer")
    loan_application_id: Optional[str] = Field(None, description="ID of the loan application if journey started")

    @model_validator(mode='after')
    def validate_offer_dates(self) -> 'OfferBase':
        """
        Validates that the offer_end_date is not before the offer_start_date.
        This validator runs after all fields have been validated.
        """
        if self.offer_start_date and self.offer_end_date and self.offer_end_date < self.offer_start_date:
            raise ValueError('Offer end date cannot be before start date')
        return self

# Schema for creating a new offer (inherits all fields from OfferBase)
class OfferCreate(OfferBase):
    pass

# Schema for updating an existing offer. All fields are optional as they might not all be updated.
class OfferUpdate(BaseModel):
    customer_id: Optional[uuid.UUID] = Field(None, description="Unique identifier for the customer")
    offer_type: Optional[str] = Field(None, description="Type of offer, e.g., 'Fresh', 'Enrich', 'New-old', 'New-new'")
    offer_status: Optional[str] = Field(None, description="Current status of the offer, e.g., 'Active', 'Inactive', 'Expired', 'Duplicate'")
    product_type: Optional[str] = Field(None, description="Product associated with the offer, e.g., 'Loyalty', 'Preapproved', 'E-aggregator', 'Insta', 'Top-up', 'Employee Loan'")
    offer_details: Optional[Dict[str, Any]] = Field(None, description="Flexible JSON storage for offer specific data")
    offer_start_date: Optional[date] = Field(None, description="Date when the offer becomes active")
    offer_end_date: Optional[date] = Field(None, description="Date when the offer expires")
    is_journey_started: Optional[bool] = Field(None, description="Flag indicating if a loan application journey has started for this offer")
    loan_application_id: Optional[str] = Field(None, description="ID of the loan application if journey started")

    @model_validator(mode='after')
    def validate_offer_dates_update(self) -> 'OfferUpdate':
        """
        Validates that the offer_end_date is not before the offer_start_date during updates.
        Only validates if both dates are provided in the update payload.
        """
        if self.offer_start_date and self.offer_end_date and self.offer_end_date < self.offer_start_date:
            raise ValueError('Offer end date cannot be before start date')
        return self

# Schema for an offer as retrieved from the database (includes DB-generated fields)
class OfferInDB(OfferBase):
    offer_id: uuid.UUID = Field(..., description="Unique identifier for the offer")
    created_at: datetime = Field(..., description="Timestamp when the offer record was created")
    updated_at: datetime = Field(..., description="Timestamp when the offer record was last updated")

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode for Pydantic

# Schema for offer history records as retrieved from the database
class OfferHistoryInDB(BaseModel):
    history_id: uuid.UUID = Field(..., description="Unique identifier for the history record")
    offer_id: uuid.UUID = Field(..., description="ID of the offer this history record pertains to")
    customer_id: uuid.UUID = Field(..., description="ID of the customer this history record pertains to")
    change_timestamp: datetime = Field(..., description="Timestamp of the status change")
    old_offer_status: str = Field(..., description="Previous status of the offer")
    new_offer_status: str = Field(..., description="New status of the offer")
    change_reason: Optional[str] = Field(None, description="Reason for the status change")
    snapshot_offer_details: Dict[str, Any] = Field(default_factory=dict, description="Snapshot of offer details at the time of change")

    model_config = ConfigDict(from_attributes=True)

# Schema for Moengage file export (based on FR54: "The system shall generate a Moengage format file in .csv format.")
# The exact fields for Moengage are an ambiguity (Q10), so these are illustrative based on common campaign needs.
class MoengageOfferExport(BaseModel):
    customer_id: uuid.UUID = Field(..., description="Unique customer identifier")
    mobile_number: str = Field(..., description="Customer's mobile number for Moengage targeting")
    offer_id: uuid.UUID = Field(..., description="Unique offer identifier")
    product_type: str = Field(..., description="Loan product type of the offer")
    offer_amount: Optional[float] = Field(None, description="Example: Loan amount offered")
    offer_expiry_date: date = Field(..., description="Date when the offer expires")
    campaign_id: Optional[str] = Field(None, description="Identifier for the campaign this offer is part of")
    # This field can hold any additional dynamic data required by Moengage,
    # which might be extracted from `offer_details` or `customer_attributes`.
    additional_moengage_data: Dict[str, Any] = Field(default_factory=dict, description="Any other dynamic data required by Moengage")

    model_config = ConfigDict(from_attributes=True)