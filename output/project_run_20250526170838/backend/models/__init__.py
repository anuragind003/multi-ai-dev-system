from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, DateTime, func

# Initialize the SQLAlchemy instance
db = SQLAlchemy()

class BaseModel(db.Model):
    """
    Base model that provides common fields like created_at and updated_at.
    All other models should inherit from this class.
    """
    __abstract__ = True  # This tells SQLAlchemy not to create a table for this class

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        """Provides a string representation of the model instance for debugging."""
        # Attempt to get the primary key name for a more informative representation
        pk_name = None
        if self.__mapper__.primary_key:
            pk_name = self.__mapper__.primary_key[0].name
        
        if pk_name and hasattr(self, pk_name):
            return f"<{self.__class__.__name__} {pk_name}={getattr(self, pk_name)}>"
        return f"<{self.__class__.__name__} object>"

    def to_dict(self):
        """Converts the model instance to a dictionary, excluding SQLAlchemy internal attributes."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

# Import all specific model classes here so they are registered with SQLAlchemy
# and can be easily imported from the 'models' package (e.g., from .models import Customer).
# These files (e.g., customer.py, offer.py) will contain the actual class definitions.
from .customer import Customer
from .offer import Offer
from .event import Event
from .campaign_metric import CampaignMetric
from .ingestion_log import IngestionLog