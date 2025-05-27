import uuid
from datetime import datetime, date

# Assuming db is initialized in backend/extensions.py
# and the Flask app context is available when this model is used.
from backend.extensions import db


class Offer(db.Model):
    """
    Represents an offer in the Customer Data Platform.

    Attributes:
        offer_id (str): Unique identifier for the offer (UUID).
        customer_id (str): Foreign key linking to the Customer model.
        offer_type (str): Type of offer (e.g., 'Fresh', 'Enrich', 'New-old', 'New-new').
                          (FR17: maintain flags for Offer types)
        offer_status (str): Current status of the offer (e.g., 'Active', 'Inactive', 'Expired').
                            (FR16: maintain flags for Offer statuses)
        propensity (str): Propensity score/category from analytics.
                          (FR18: maintain analytics-defined flags for Propensity)
        start_date (date): Date when the offer becomes active.
        end_date (date): Date when the offer expires.
        channel (str): Channel through which the offer was made (for attribution logic).
        created_at (datetime): Timestamp when the offer record was created.
        updated_at (datetime): Timestamp when the offer record was last updated.
    """
    __tablename__ = 'offers'

    offer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.Text)
    offer_status = db.Column(db.Text, default='Active')
    propensity = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    channel = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationship to Customer model
    # This allows accessing offer.customer and customer.offers
    customer = db.relationship('Customer', backref='offers', lazy=True)

    def __init__(self, customer_id, offer_type, propensity, start_date, end_date, channel,
                 offer_status='Active'):
        """
        Initializes a new Offer instance.
        """
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.propensity = propensity
        self.start_date = start_date
        self.end_date = end_date
        self.channel = channel
        self.offer_status = offer_status

    def __repr__(self):
        """
        Returns a string representation of the Offer object.
        """
        return (f"<Offer(id='{self.offer_id}', customer_id='{self.customer_id}', "
                f"type='{self.offer_type}', status='{self.offer_status}')>")

    def to_dict(self):
        """
        Converts the Offer object to a dictionary for API responses.
        Dates and datetimes are converted to ISO format strings.
        """
        return {
            'offer_id': self.offer_id,
            'customer_id': self.customer_id,
            'offer_type': self.offer_type,
            'offer_status': self.offer_status,
            'propensity': self.propensity,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'channel': self.channel,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def save(self):
        """
        Adds the current offer instance to the database session and commits.
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        Deletes the current offer instance from the database session and commits.
        """
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, offer_id):
        """
        Retrieves an offer by its unique ID.

        Args:
            offer_id (str): The ID of the offer to retrieve.

        Returns:
            Offer: The Offer object if found, otherwise None.
        """
        return cls.query.get(offer_id)

    @classmethod
    def get_all(cls):
        """
        Retrieves all offers from the database.

        Returns:
            list[Offer]: A list of all Offer objects.
        """
        return cls.query.all()

    @classmethod
    def get_offers_by_customer_id(cls, customer_id):
        """
        Retrieves all offers associated with a specific customer ID.

        Args:
            customer_id (str): The ID of the customer.

        Returns:
            list[Offer]: A list of Offer objects for the given customer.
        """
        return cls.query.filter_by(customer_id=customer_id).all()

    @classmethod
    def get_active_offers_for_customer(cls, customer_id):
        """
        Retrieves all active offers for a given customer.

        Args:
            customer_id (str): The ID of the customer.

        Returns:
            list[Offer]: A list of active Offer objects for the given customer.
        """
        return cls.query.filter_by(customer_id=customer_id, offer_status='Active').all()

    @classmethod
    def update_offer_status(cls, offer_id, new_status):
        """
        Updates the status of a specific offer.

        Args:
            offer_id (str): The ID of the offer to update.
            new_status (str): The new status to set (e.g., 'Active', 'Inactive', 'Expired').

        Returns:
            bool: True if the offer was found and updated, False otherwise.
        """
        offer = cls.get_by_id(offer_id)
        if offer:
            offer.offer_status = new_status
            offer.save()
            return True
        return False

    @classmethod
    def expire_offers_based_on_end_date(cls):
        """
        Marks offers as 'Expired' if their end_date is in the past and their status is 'Active'.
        This method is intended to be called by a scheduled background task.

        Note: This method handles FR41 (mark offers as expired based on offer end dates
        for non-journey started customers). The more complex logic for 'journey started'
        customers (FR14, FR43) would typically involve checking the 'events' table or
        a 'loan_application_number' status, and would likely be implemented in a
        service layer that orchestrates interactions between Offer and Event models.

        Returns:
            int: The number of offers that were marked as 'Expired'.
        """
        today = date.today()
        offers_to_expire = cls.query.filter(
            cls.offer_status == 'Active',
            cls.end_date < today
        ).all()

        count = 0
        for offer in offers_to_expire:
            offer.offer_status = 'Expired'
            db.session.add(offer)
            count += 1
        db.session.commit()
        return count