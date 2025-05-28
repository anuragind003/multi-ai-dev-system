from app import db
from .customer import Customer
from .offer import Offer
from .customer_event import CustomerEvent
from .campaign import Campaign
from .data_ingestion_log import DataIngestionLog

# This __init__.py file makes the 'models' directory a Python package.
# By importing the individual model classes here, they can be accessed
# directly from `app.models` (e.g., `from app.models import Customer`).
# The `db` object is imported from the main `app` instance,
# assuming it's initialized there (as seen in `app.py` context).