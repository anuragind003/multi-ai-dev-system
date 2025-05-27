import uuid
from datetime import datetime, date
from src.extensions import db

class Offer(db.Model):
    """
    Represents an offer in the CDP system.
    Corresponds to the 'offers' table in the database schema.
    """
    __tablename__ = 'offers'

    offer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.Text, nullable=False)  # e.g., 'Fresh', 'Enrich', 'New-old', 'New-new' (FR17)
    offer_status = db.Column(db.Text, nullable=False, default='Active')  # e.g., 'Active', 'Inactive', 'Expired' (FR16)
    propensity = db.Column(db.Text)  # Values passed from Offermart (FR18)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    channel = db.Column(db.Text)  # For attribution logic (FR21)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to Customer model (assuming Customer model is defined in src/models/customer.py)
    # The backref 'offers_rel' is used to avoid potential naming conflicts if 'offers' is used elsewhere.
    customer = db.relationship('Customer', backref=db.backref('offers_rel', lazy=True))

    def __init__(self, customer_id, offer_type, start_date, end_date, propensity=None, channel=None, offer_status='Active'):
        self.customer_id = customer_id
        self.offer_type = offer_type
        self.start_date = start_date
        self.end_date = end_date
        self.propensity = propensity
        self.channel = channel
        self.offer_status = offer_status

    def __repr__(self):
        return f"<Offer {self.offer_id} for Customer {self.customer_id} - Status: {self.offer_status}>"

    def to_dict(self):
        """Serializes the Offer object to a dictionary for API responses."""
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

    @classmethod
    def create(cls, data):
        """
        Creates a new offer record in the database.
        :param data: Dictionary containing offer details. Expected keys: 'customer_id', 'offer_type',
                     'start_date' (date object), 'end_date' (date object). Optional: 'propensity', 'channel', 'offer_status'.
        :return: The created Offer object or None if creation fails.
        """
        try:
            new_offer = cls(
                customer_id=data['customer_id'],
                offer_type=data['offer_type'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                propensity=data.get('propensity'),
                channel=data.get('channel'),
                offer_status=data.get('offer_status', 'Active')
            )
            db.session.add(new_offer)
            db.session.commit()
            return new_offer
        except Exception as e:
            db.session.rollback()
            print(f"Error creating offer: {e}")
            return None

    @classmethod
    def get_by_id(cls, offer_id):
        """Retrieves an offer by its ID."""
        return cls.query.get(offer_id)

    @classmethod
    def get_by_customer_id(cls, customer_id, status=None):
        """
        Retrieves all offers for a given customer, optionally filtered by status.
        :param customer_id: The ID of the customer.
        :param status: Optional status to filter offers (e.g., 'Active', 'Expired').
        :return: List of Offer objects.
        """
        query = cls.query.filter_by(customer_id=customer_id)
        if status:
            query = query.filter_by(offer_status=status)
        return query.all()

    @classmethod
    def update(cls, offer_id, data):
        """
        Updates an existing offer record.
        :param offer_id: The ID of the offer to update.
        :param data: Dictionary containing fields to update.
        :return: The updated Offer object or None if not found/update fails.
        """
        offer = cls.query.get(offer_id)
        if not offer:
            return None
        try:
            for key, value in data.items():
                if hasattr(offer, key):
                    setattr(offer, key, value)
            db.session.commit()
            return offer
        except Exception as e:
            db.session.rollback()
            print(f"Error updating offer {offer_id}: {e}")
            return None

    @classmethod
    def update_offer_status(cls, offer_id, new_status):
        """
        Updates the status of a specific offer.
        :param offer_id: The ID of the offer to update.
        :param new_status: The new status (e.g., 'Active', 'Inactive', 'Expired').
        :return: The updated Offer object or None if not found/update fails.
        """
        offer = cls.query.get(offer_id)
        if not offer:
            return None
        try:
            offer.offer_status = new_status
            db.session.commit()
            return offer
        except Exception as e:
            db.session.rollback()
            print(f"Error updating status for offer {offer_id}: {e}")
            return None

    @classmethod
    def expire_offers_by_end_date(cls):
        """
        Marks offers as 'Expired' if their end_date is in the past and they are currently 'Active'.
        (FR41: The system shall mark offers as expired based on offer end dates for non-journey started customers.)
        This method handles the date-based expiration. The business logic for "non-journey started customers"
        should be handled by a service layer that calls this method or filters results before calling.
        :return: Number of offers updated.
        """
        try:
            today = date.today()
            # Find active offers whose end_date is before today
            offers_to_expire = cls.query.filter(
                cls.offer_status == 'Active',
                cls.end_date < today
            ).all()

            updated_count = 0
            for offer in offers_to_expire:
                offer.offer_status = 'Expired'
                updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
            return updated_count
        except Exception as e:
            db.session.rollback()
            print(f"Error expiring offers by end date: {e}")
            return 0

    # FR43: The system shall mark offers as expired for journey started customers whose LAN (Loan Application Number) validity is over.
    # This specific logic is more complex as it involves checking the customer's loan application status,
    # which is likely managed across the Customer and Event models. This functionality would typically
    # reside in a service layer that orchestrates interactions between these models.
    # A placeholder for such a method, if it were to be implemented directly in the model, might look like:
    # @classmethod
    # def expire_offers_for_journey_completed_customers(cls, customer_ids_with_expired_lan):
    #     """
    #     Marks offers as 'Expired' for customers whose loan application journey has completed/expired.
    #     This method assumes a list of customer_ids whose LAN validity is over is provided by a higher layer.
    #     """
    #     try:
    #         updated_count = cls.query.filter(
    #             cls.customer_id.in_(customer_ids_with_expired_lan),
    #             cls.offer_status == 'Active'
    #         ).update({'offer_status': 'Expired'}, synchronize_session=False)
    #         db.session.commit()
    #         return updated_count
    #     except Exception as e:
    #         db.session.rollback()
    #         print(f"Error expiring offers for journey completed customers: {e}")
    #         return 0