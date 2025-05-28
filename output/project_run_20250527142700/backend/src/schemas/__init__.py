from marshmallow import Schema, fields

class BaseSchema(Schema):
    """
    Base schema for common fields like timestamps.
    All other schemas can inherit from this.
    """
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

# Specific schemas (e.g., CustomerSchema, OfferSchema) will be defined in
# separate files within this 'schemas' directory (e.g., customer.py, offer.py)
# and can then be imported here if desired for easier access.
# For example:
# from .customer import CustomerSchema
# from .offer import OfferSchema
# from .event import EventSchema
# from .campaign import CampaignSchema