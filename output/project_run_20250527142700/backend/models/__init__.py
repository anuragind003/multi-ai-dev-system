from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy. The 'db' object will be initialized with the Flask app
# later in the main application's create_app function.
db = SQLAlchemy()

# Import all model classes here to ensure they are registered with SQLAlchemy
# and are accessible when 'backend.models' is imported.
from .customer import Customer
from .offer import Offer
from .offer_history import OfferHistory
from .event import Event
from .campaign import Campaign