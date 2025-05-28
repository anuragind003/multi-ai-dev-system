import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import func
from backend.extensions import db # Assuming db is initialized in backend/extensions.py
from sqlalchemy import or_

class Customer(db.Model):
    """
    Represents a de-duplicated customer profile in the CDP system.
    This model stores core customer identifiers and attributes.
    """
    __tablename__ = 'customers'

    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    mobile_number = db.Column(db.String(20), unique=True, nullable=True)
    pan_number = db.Column(db.String(10), unique=True, nullable=True)
    aadhaar_number = db.Column(db.String(12), unique=True, nullable=True)
    ucid_number = db.Column(db.String(50), unique=True, nullable=True)
    customer_360_id = db.Column(db.String(50), nullable=True) # For integration with Customer 360 (FR5, NFR17)
    is_dnd = db.Column(db.Boolean, default=False, nullable=False) # FR24
    segment = db.Column(db.String(50), nullable=True) # C1-C8, etc. (FR15, FR21)
    attributes = db.Column(JSONB, nullable=True) # For other customer attributes (FR15)
    created_at = db.Column(db.TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column(db.TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # A customer can have multiple offers (FR16, FR17, FR20)
    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    # A customer can have multiple events (FR23, FR25, FR26, FR27)
    events = db.relationship('Event', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.customer_id} - Mobile: {self.mobile_number or 'N/A'}>"

    def to_dict(self):
        """
        Converts the Customer object to a dictionary.
        Useful for API responses and serialization.
        """
        return {
            'customer_id': str(self.customer_id),
            'mobile_number': self.mobile_number,
            'pan_number': self.pan_number,
            'aadhaar_number': self.aadhaar_number,
            'ucid_number': self.ucid_number,
            'customer_360_id': self.customer_360_id,
            'is_dnd': self.is_dnd,
            'segment': self.segment,
            'attributes': self.attributes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def find_by_id(cls, customer_id: str):
        """
        Finds a customer by their UUID.
        """
        return cls.query.get(customer_id)

    @classmethod
    def find_by_identifiers(cls, mobile_number: str = None, pan_number: str = None, 
                            aadhaar_number: str = None, ucid_number: str = None):
        """
        Finds a customer by any of the unique identifiers (Mobile, PAN, Aadhaar, UCID).
        This method supports the deduplication logic (FR3).
        It uses OR logic to find a match if any of the provided identifiers exist.
        """
        conditions = []
        if mobile_number:
            conditions.append(cls.mobile_number == mobile_number)
        if pan_number:
            conditions.append(cls.pan_number == pan_number)
        if aadhaar_number:
            conditions.append(cls.aadhaar_number == aadhaar_number)
        if ucid_number:
            conditions.append(cls.ucid_number == ucid_number)
        
        if conditions:
            return cls.query.filter(or_(*conditions)).first()
        return None

    def save(self):
        """
        Adds a new customer or updates an existing one in the database.
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        Deletes the customer from the database.
        """
        db.session.delete(self)
        db.session.commit()

    def update_attributes(self, new_attributes: dict):
        """
        Updates the JSONB 'attributes' field with new data.
        This performs a merge if 'attributes' already exists.
        """
        if self.attributes is None:
            self.attributes = {}
        self.attributes.update(new_attributes)
        self.updated_at = func.now() # Manually update timestamp if not using onupdate for JSONB changes
        self.save()

    def set_dnd_status(self, status: bool):
        """
        Sets the Do Not Disturb (DND) status for the customer. (FR24)
        """
        self.is_dnd = status
        self.updated_at = func.now()
        self.save()

    def update_segment(self, segment: str):
        """
        Updates the customer's segment. (FR15, FR21)
        """
        self.segment = segment
        self.updated_at = func.now()
        self.save()