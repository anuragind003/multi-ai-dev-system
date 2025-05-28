from marshmallow import Schema, fields
from marshmallow.validate import Length, OneOf

# Define choices for certain fields based on BRD and database schema
OFFER_STATUS_CHOICES = ['Active', 'Inactive', 'Expired']
OFFER_TYPE_CHOICES = ['Fresh', 'Enrich', 'New-old', 'New-new']
OFFER_SOURCE_SYSTEM_CHOICES = ['Offermart', 'E-aggregator']


class OfferSchema(Schema):
    """
    Marshmallow schema for serializing and deserializing Offer data.
    Corresponds to the 'offers' table in the database.
    """
    offer_id = fields.UUID(
        dump_only=True,
        required=True,
        metadata={"description": "Unique identifier for the offer"}
    )
    customer_id = fields.UUID(
        required=True,
        metadata={"description": "Foreign key to the customer table"}
    )
    source_offer_id = fields.String(
        validate=Length(max=100),
        allow_none=True,
        metadata={"description": "Original ID from Offermart/E-aggregator"}
    )
    offer_type = fields.String(
        validate=OneOf(OFFER_TYPE_CHOICES),
        allow_none=True,
        metadata={"description": "Type of offer: Fresh, Enrich, New-old, New-new (FR17)"}
    )
    offer_status = fields.String(
        validate=OneOf(OFFER_STATUS_CHOICES),
        allow_none=True,
        metadata={"description": "Status of the offer: Active, Inactive, Expired (FR16)"}
    )
    propensity = fields.String(
        validate=Length(max=50),
        allow_none=True,
        metadata={"description": "Propensity value from Offermart (FR19)"}
    )
    loan_application_number = fields.String(
        validate=Length(max=100),
        allow_none=True,
        metadata={"description": "Loan Application Number (LAN)"}
    )
    valid_until = fields.DateTime(
        format='iso',
        allow_none=True,
        metadata={"description": "Timestamp indicating when the offer is valid until"}
    )
    source_system = fields.String(
        validate=OneOf(OFFER_SOURCE_SYSTEM_CHOICES),
        allow_none=True,
        metadata={"description": "System from which the offer originated (e.g., Offermart, E-aggregator)"}
    )
    channel = fields.String(
        validate=Length(max=50),
        allow_none=True,
        metadata={"description": "Channel through which the offer was made (for attribution)"}
    )
    is_duplicate = fields.Boolean(
        metadata={"description": "Flag indicating if this offer is a duplicate (FR6)"}
    )
    original_offer_id = fields.UUID(
        allow_none=True,
        metadata={"description": "Points to the offer it duplicated/enriched, if applicable"}
    )
    created_at = fields.DateTime(
        format='iso',
        dump_only=True,
        metadata={"description": "Timestamp of offer creation"}
    )
    updated_at = fields.DateTime(
        format='iso',
        dump_only=True,
        metadata={"description": "Timestamp of last offer update"}
    )


class CustomerSchema(Schema):
    """
    Marshmallow schema for serializing and deserializing Customer data.
    Corresponds to the 'customers' table in the database.
    """
    customer_id = fields.UUID(
        dump_only=True,
        required=True,
        metadata={"description": "Unique identifier for the customer"}
    )
    mobile_number = fields.String(
        validate=Length(max=20),
        allow_none=True,  # Allow none as other unique identifiers exist for deduplication
        metadata={"description": "Customer's mobile number (unique, FR3)"}
    )
    pan_number = fields.String(
        validate=Length(max=10),
        allow_none=True,
        metadata={"description": "Customer's PAN number (unique, FR3)"}
    )
    aadhaar_number = fields.String(
        validate=Length(max=12),
        allow_none=True,
        metadata={"description": "Customer's Aadhaar reference number (unique, FR3)"}
    )
    ucid_number = fields.String(
        validate=Length(max=50),
        allow_none=True,
        metadata={"description": "Customer's UCID number (unique, FR3)"}
    )
    customer_360_id = fields.String(
        validate=Length(max=50),
        allow_none=True,
        metadata={"description": "ID from Customer 360 system (FR5)"}
    )
    is_dnd = fields.Boolean(
        metadata={"description": "Flag indicating if the customer is on Do Not Disturb list (FR24)"}
    )
    segment = fields.String(
        validate=Length(max=50),
        allow_none=True,
        metadata={"description": "Customer segment (e.g., C1-C8, FR15, FR21)"}
    )
    attributes = fields.Dict(
        allow_none=True,
        metadata={"description": "JSONB field for additional customer attributes (FR15)"}
    )
    created_at = fields.DateTime(
        format='iso',
        dump_only=True,
        metadata={"description": "Timestamp of customer creation"}
    )
    updated_at = fields.DateTime(
        format='iso',
        dump_only=True,
        metadata={"description": "Timestamp of last customer update"}
    )

    # Nested offers for customer profile retrieval (as per API endpoint design)
    offers = fields.List(
        fields.Nested(OfferSchema),
        dump_only=True,  # Offers are typically loaded with the customer, not created/updated via customer schema
        metadata={"description": "List of offers associated with this customer"}
    )


# Instantiate schemas for use in API routes and services
customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)
offer_schema = OfferSchema()
offers_schema = OfferSchema(many=True)