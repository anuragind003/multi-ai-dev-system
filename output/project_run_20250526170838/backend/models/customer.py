import uuid
from datetime import datetime

from backend.extensions import db


class Customer(db.Model):
    """
    Represents a customer in the Customer Data Platform (CDP).
    This model stores core customer identifiers and attributes.
    """
    __tablename__ = 'customers'

    customer_id = db.Column(db.Text, primary_key=True,
                            default=lambda: str(uuid.uuid4()))
    mobile_number = db.Column(db.Text, unique=True, nullable=True)
    pan_number = db.Column(db.Text, unique=True, nullable=True)
    aadhaar_number = db.Column(db.Text, unique=True, nullable=True)
    ucid_number = db.Column(db.Text, unique=True, nullable=True)
    loan_application_number = db.Column(db.Text, unique=True, nullable=True)
    dnd_flag = db.Column(db.Boolean, default=False, nullable=False)
    segment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow,
                           nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # Assuming Offer model is defined in backend.models.offer
    offers = db.relationship('Offer', backref='customer', lazy=True,
                             cascade="all, delete-orphan")
    # Assuming Event model is defined in backend.models.event
    events = db.relationship('Event', backref='customer', lazy=True,
                             cascade="all, delete-orphan")

    def __repr__(self):
        return (f"<Customer {self.customer_id} | Mobile: {self.mobile_number} "
                f"| PAN: {self.pan_number}>")

    def to_dict(self):
        """
        Converts the Customer object to a dictionary for API responses.
        """
        return {
            'customer_id': self.customer_id,
            'mobile_number': self.mobile_number,
            'pan_number': self.pan_number,
            'aadhaar_number': self.aadhaar_number,
            'ucid_number': self.ucid_number,
            'loan_application_number': self.loan_application_number,
            'dnd_flag': self.dnd_flag,
            'segment': self.segment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_by_id(cls, customer_id):
        """
        Retrieves a customer by their unique customer_id.
        """
        return cls.query.get(customer_id)

    @classmethod
    def get_by_identifiers(cls, mobile_number=None, pan_number=None,
                           aadhaar_number=None, ucid_number=None,
                           loan_application_number=None):
        """
        Retrieves a customer based on any of the unique identifiers.
        Used for deduplication logic (FR3, FR4, FR5, FR6).
        """
        query = cls.query
        conditions = []

        if mobile_number:
            conditions.append(cls.mobile_number == mobile_number)
        if pan_number:
            conditions.append(cls.pan_number == pan_number)
        if aadhaar_number:
            conditions.append(cls.aadhaar_number == aadhaar_number)
        if ucid_number:
            conditions.append(cls.ucid_number == ucid_number)
        if loan_application_number:
            conditions.append(cls.loan_application_number ==
                               loan_application_number)

        if not conditions:
            return None  # No identifiers provided

        # Use OR to find a match on any of the provided identifiers
        return query.filter(db.or_(*conditions)).first()

    @classmethod
    def create(cls, data):
        """
        Creates a new customer record.
        Args:
            data (dict): Dictionary containing customer details.
                         Expected keys: mobile_number, pan_number,
                         aadhaar_number, ucid_number,
                         loan_application_number, dnd_flag, segment.
        Returns:
            Customer: The newly created Customer object, or None if creation fails.
        """
        try:
            customer = cls(
                mobile_number=data.get('mobile_number'),
                pan_number=data.get('pan_number'),
                aadhaar_number=data.get('aadhaar_number'),
                ucid_number=data.get('ucid_number'),
                loan_application_number=data.get('loan_application_number'),
                dnd_flag=data.get('dnd_flag', False),
                segment=data.get('segment')
            )
            db.session.add(customer)
            db.session.commit()
            return customer
        except Exception as e:
            db.session.rollback()
            # In a real application, use a proper logger (e.g., Flask's app.logger)
            print(f"Error creating customer: {e}")
            return None

    def update(self, data):
        """
        Updates an existing customer record.
        Args:
            data (dict): Dictionary containing updated customer details.
        Returns:
            bool: True if update is successful, False otherwise.
        """
        try:
            for key, value in data.items():
                # Prevent updating primary key or creation timestamp
                if hasattr(self, key) and key not in ['customer_id', 'created_at']:
                    setattr(self, key, value)
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error updating customer {self.customer_id}: {e}")
            return False

    def set_dnd_flag(self, flag):
        """
        Sets the DND (Do Not Disturb) flag for the customer (FR23).
        Args:
            flag (bool): True to set DND, False to unset.
        Returns:
            bool: True if update is successful, False otherwise.
        """
        try:
            self.dnd_flag = flag
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error setting DND flag for customer {self.customer_id}: {e}")
            return False

    @classmethod
    def get_customer_profile_view(cls, customer_id):
        """
        Retrieves a comprehensive view of a customer, including their offers
        and journey stages, as required by FR2 and the API endpoint
        /customers/{customer_id}.
        This method assumes relationships with Offer and Event models are defined
        and they have a .to_dict() method.
        """
        customer = cls.query.options(
            db.joinedload(cls.offers),
            db.joinedload(cls.events)
        ).get(customer_id)

        if not customer:
            return None

        customer_data = customer.to_dict()
        # Filter for active offers as per typical "current offers" view
        customer_data['current_offers'] = [
            offer.to_dict() for offer in customer.offers
            if offer.offer_status == 'Active'
        ]
        customer_data['journey_stages'] = [
            event.to_dict() for event in customer.events
        ]
        return customer_data