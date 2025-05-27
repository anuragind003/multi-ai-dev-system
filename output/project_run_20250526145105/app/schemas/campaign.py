from uuid import UUID
from datetime import datetime, date
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

# --- Campaign Event Schemas ---

class CampaignEventBase(BaseModel):
    """Base schema for a campaign event, reflecting common attributes."""
    customer_id: UUID = Field(..., description="Unique identifier of the customer associated with this event.")
    offer_id: Optional[UUID] = Field(None, description="Unique identifier of the offer related to this event, if applicable.")
    event_source: str = Field(..., max_length=50, description="The system or origin from which the event was received (e.g., 'Moengage', 'LOS').")
    event_type: str = Field(..., max_length=100, description="The specific type of event that occurred (e.g., 'SMS_SENT', 'CLICK', 'CONVERSION', 'LOGIN').")
    event_details: Dict[str, Any] = Field(..., description="A flexible JSONB field to store raw event data or additional, unstructured details.")

class CampaignEventCreate(CampaignEventBase):
    """Schema for creating a new campaign event record. Inherits from CampaignEventBase."""
    # No additional fields are typically required for creation beyond the base data.
    pass

class CampaignEventResponse(CampaignEventBase):
    """Schema for returning campaign event data, including system-generated fields like ID and timestamp."""
    event_id: UUID = Field(..., description="Unique identifier of the campaign event record in the database.")
    event_timestamp: datetime = Field(..., description="Timestamp indicating when the event record was created or last updated.")

    class Config:
        # This setting is crucial for Pydantic v2 to work seamlessly with ORM models (like SQLAlchemy).
        # It allows Pydantic to read attributes from ORM objects as if they were dictionary keys.
        from_attributes = True

# --- Campaign Summary/Report Schemas ---

class CampaignSummary(BaseModel):
    """
    Schema for aggregated campaign performance data, as outlined in Functional Requirement FR48.
    This represents a summary view of a campaign's overall outcomes and metrics.
    """
    campaign_unique_identifier: str = Field(..., description="A unique identifier or name for the specific campaign being summarized.")
    date_of_campaign: date = Field(..., description="The primary date on which the campaign was executed or its data pertains to.")
    attempted_count: int = Field(..., ge=0, description="Total number of customers targeted or attempts made in the campaign.")
    successfully_sent_count: int = Field(..., ge=0, description="Number of communications or offers successfully delivered to customers.")
    failed_count: int = Field(..., ge=0, description="Number of communications or offers that failed to be delivered.")
    success_rate: float = Field(..., ge=0.0, le=100.0, description="The calculated success rate of the campaign, typically (successfully_sent / attempted) * 100.")
    conversion_rate: float = Field(..., ge=0.0, le=100.0, description="The calculated conversion rate of the campaign (e.g., number of loan applications started / attempted) * 100.")

    class Config:
        from_attributes = True

# --- Moengage File Generation Related Schemas ---
# The API endpoint for Moengage file generation is a GET request that directly returns CSV content.
# Therefore, a Pydantic schema for the request body or the direct file content response is not
# typically defined in this file. If there were an endpoint to *list* generated files or their
# metadata, a schema for that metadata would be appropriate, but it's not explicitly required
# by the current API design for the direct download endpoint.