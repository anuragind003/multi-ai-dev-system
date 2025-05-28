from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text, or_

# Assuming db is initialized in app.extensions
# This import is crucial for the model to connect to the SQLAlchemy instance.
from app.extensions import db

class Customer(db.Model):
    """
    Represents a customer profile in the CDP.
    Corresponds to the 'customers' table in the database schema.

    Functional Requirements addressed:
    - FR2: The system shall provide a single profile view of the customer for Consumer Loan Products
           based on mobile number, PAN, Aadhaar reference number, UCID, or previous loan application number.
    - FR14: The system shall maintain different customer attributes and customer segments.
    - FR19: The system shall maintain customer segments like C1 to C8.
    - FR21: The system shall store event data from Moengage and LOS in the LTFS Offer CDP, avoiding DND Customers.
    """
    __tablename__ = 'customers'

    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    pan = db.Column(db.String(10), unique=True)
    aadhaar_ref_number = db.Column(db.String(12), unique=True)
    ucid = db.Column(db.String(50), unique=True)
    previous_loan_app_number = db.Column(db.String(50), unique=True)
    customer_attributes = db.Column(JSONB)
    customer_segment = db.Column(db.String(10))
    is_dnd = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships: A customer can have multiple offers and events.
    # These relationships are defined here for completeness of the model,
    # assuming Offer and CustomerEvent models exist in app.models.
    # 'backref' creates a 'customer' attribute on the related model (e.g., offer.customer).
    # 'cascade="all, delete-orphan"' ensures that if a customer is deleted,
    # their associated offers and events are also deleted from the database.
    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('CustomerEvent', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        """
        Provides a string representation of the Customer object.
        """
        return f"<Customer {self.customer_id} | Mobile: {self.mobile_number}>"

    def to_dict(self, include_relationships=False):
        """
        Converts the Customer object to a dictionary, useful for API responses.
        """
        data = {
            'customer_id': str(self.customer_id),
            'mobile_number': self.mobile_number,
            'pan': self.pan,
            'aadhaar_ref_number': self.aadhaar_ref_number,
            'ucid': self.ucid,
            'previous_loan_app_number': self.previous_loan_app_number,
            'customer_attributes': self.customer_attributes,
            'customer_segment': self.customer_segment,
            'is_dnd': self.is_dnd,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_relationships:
            # Note: This will trigger lazy loading if relationships are not already loaded.
            # Ensure Offer and CustomerEvent models also have a .to_dict() method defined.
            data['offers'] = [offer.to_dict() for offer in self.offers] if self.offers else []
            data['events'] = [event.to_dict() for event in self.events] if self.events else []
        return data

    @classmethod
    def get_by_identifiers(cls, mobile_number=None, pan=None, aadhaar_ref_number=None, ucid=None, previous_loan_app_number=None):
        """
        Retrieves a customer based on any of the unique identifiers provided.
        This method supports FR2 by allowing a single profile view based on multiple identifiers.
        """
        conditions = []
        if mobile_number:
            conditions.append(cls.mobile_number == mobile_number)
        if pan:
            conditions.append(cls.pan == pan)
        if aadhaar_ref_number:
            conditions.append(cls.aadhaar_ref_number == aadhaar_ref_number)
        if ucid:
            conditions.append(cls.ucid == ucid)
        if previous_loan_app_number:
            conditions.append(cls.previous_loan_app_number == previous_loan_app_number)

        if not conditions:
            return None # No identifiers provided

        # Use 'or_' to find a customer matching any of the provided unique identifiers
        return cls.query.filter(or_(*conditions)).first()

    @classmethod
    def create_or_update(cls, data: dict):
        """
        Creates a new customer record or updates an existing one based on unique identifiers.
        This method is central to the deduplication logic (FR3, FR4).

        Args:
            data (dict): A dictionary containing customer attributes.
                         Expected to include at least one unique identifier
                         (mobile_number, pan, aadhaar_ref_number, ucid, previous_loan_app_number).

        Returns:
            Customer: The created or updated Customer object.
        """
        customer = cls.get_by_identifiers(
            mobile_number=data.get('mobile_number'),
            pan=data.get('pan'),
            aadhaar_ref_number=data.get('aadhaar_ref_number'),
            ucid=data.get('ucid'),
            previous_loan_app_number=data.get('previous_loan_app_number')
        )

        if customer:
            # Update existing customer's attributes
            for key, value in data.items():
                # Only update if the key is a valid attribute of the model
                # and the new value is not None.
                if hasattr(customer, key) and value is not None:
                    # Special handling for unique fields:
                    # Only update if the current value is None (filling a gap)
                    # or if the new value is different from the current one.
                    # This prevents unnecessary updates and potential IntegrityErrors
                    # if a unique field is already populated and the new data provides the same value.
                    if key in ['mobile_number', 'pan', 'aadhaar_ref_number', 'ucid', 'previous_loan_app_number']:
                        if getattr(customer, key) is None:
                            setattr(customer, key, value)
                        elif getattr(customer, key) != value:
                            setattr(customer, key, value)
                    else:
                        setattr(customer, key, value)
            customer.updated_at = datetime.utcnow() # Update timestamp on modification
        else:
            # Create a new customer record
            customer = cls(**data)
            db.session.add(customer)

        return customer