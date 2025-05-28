import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# Import the db instance from your application's extensions or app file
# This assumes you have a file like backend/extensions.py where db = SQLAlchemy() is initialized.
from backend.extensions import db

# Import related models to establish relationships
# These imports are necessary for db.relationship to correctly link models
from .customer import Customer
from .offer_history import OfferHistory
from .event import Event


class Offer(db.Model):
    __tablename__ = 'offers'

    offer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    source_offer_id = db.Column(db.String(100))
    offer_type = db.Column(db.String(50))  # 'Fresh', 'Enrich', 'New-old', 'New-new' (FR17)
    offer_status = db.Column(db.String(50))  # 'Active', 'Inactive', 'Expired' (FR16)
    propensity = db.Column(db.String(50))  # (FR19)
    loan_application_number = db.Column(db.String(100))  # LAN (FR36)
    valid_until = db.Column(db.DateTime(timezone=True))
    source_system = db.Column(db.String(50))  # 'Offermart', 'E-aggregator'
    channel = db.Column(db.String(50))  # For attribution (FR22)
    is_duplicate = db.Column(db.Boolean, default=False)  # Flagged by deduplication (FR18)
    original_offer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('offers.offer_id'))  # Points to the offer it duplicated/enriched (FR18)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    # backref='offers' on Customer will allow customer.offers to access related offers
    customer = db.relationship('Customer', backref=db.backref('offers', lazy=True))
    # Self-referencing relationship for duplicate/enriched offers
    # remote_side specifies the column on the *remote* side of the relationship (i.e., the primary key of the 'Offer' table itself)
    original_offer = db.relationship('Offer', remote_side=[offer_id], backref='duplicate_offers')
    # backref='offer' on OfferHistory will allow history_entry.offer to access the related offer
    offer_history_entries = db.relationship('OfferHistory', backref=db.backref('offer', lazy=True), cascade="all, delete-orphan")
    # backref='offer' on Event will allow event.offer to access the related offer
    events = db.relationship('Event', backref=db.backref('offer', lazy=True), cascade="all, delete-orphan")

    def __init__(self, customer_id, source_offer_id=None, offer_type=None, offer_status='Active',
                 propensity=None, loan_application_number=None, valid_until=None,
                 source_system=None, channel=None, is_duplicate=False, original_offer_id=None):
        self.customer_id = customer_id
        self.source_offer_id = source_offer_id
        self.offer_type = offer_type
        self.offer_status = offer_status
        self.propensity = propensity
        self.loan_application_number = loan_application_number
        self.valid_until = valid_until
        self.source_system = source_system
        self.channel = channel
        self.is_duplicate = is_duplicate
        self.original_offer_id = original_offer_id

    def __repr__(self):
        return f"<Offer {self.offer_id} for Customer {self.customer_id} - Status: {self.offer_status}>"

    def to_dict(self):
        """Serializes the Offer object to a dictionary."""
        return {
            'offer_id': str(self.offer_id),
            'customer_id': str(self.customer_id),
            'source_offer_id': self.source_offer_id,
            'offer_type': self.offer_type,
            'offer_status': self.offer_status,
            'propensity': self.propensity,
            'loan_application_number': self.loan_application_number,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'source_system': self.source_system,
            'channel': self.channel,
            'is_duplicate': self.is_duplicate,
            'original_offer_id': str(self.original_offer_id) if self.original_offer_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def save(self):
        """Adds the current Offer object to the database session and commits."""
        db.session.add(self)
        db.session.commit()

    def update(self, **kwargs):
        """Updates attributes of the Offer object and commits changes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()

    def delete(self):
        """Deletes the current Offer object from the database."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, offer_id):
        """Retrieves an Offer by its ID."""
        return cls.query.get(offer_id)

    @classmethod
    def get_active_offers_for_customer(cls, customer_id):
        """Retrieves all active offers for a given customer."""
        return cls.query.filter_by(customer_id=customer_id, offer_status='Active').all()

    def mark_as_expired(self, reason="LAN validity over"):
        """
        Marks the offer status as 'Expired' and logs to history.
        (FR16: Maintain flags for Offer statuses: Active, Inactive, and Expired)
        (FR36: Mark offers as expired if LAN validity is over for journey-started customers)
        """
        if self.offer_status != 'Expired':
            old_status = self.offer_status
            self.offer_status = 'Expired'
            self.update()  # Commit the status change

            # Log to offer history (FR20: Maintain Offer history for the past 6 months)
            history_entry = OfferHistory(
                offer_id=self.offer_id,
                old_status=old_status,
                new_status='Expired',
                change_reason=reason
            )
            db.session.add(history_entry)
            db.session.commit()  # Commit history entry separately or with parent transaction

    def mark_as_duplicate(self, original_offer_id):
        """
        Marks the offer as a duplicate and links to the original offer.
        (FR18: if journey not started, flow to CDP and mark previous offer as Duplicate)
        """
        if not self.is_duplicate:
            old_status = self.offer_status
            self.is_duplicate = True
            # If this offer is the one being identified as a duplicate of an existing one,
            # then this offer itself should be marked as duplicate and potentially inactive.
            self.offer_status = 'Inactive'  # Or a specific 'Duplicate' status if defined
            self.original_offer_id = original_offer_id
            self.update()

            # Log to offer history
            history_entry = OfferHistory(
                offer_id=self.offer_id,
                old_status=old_status,
                new_status='Inactive',  # Or 'Duplicate'
                change_reason=f"Marked as duplicate of offer {original_offer_id}"
            )
            db.session.add(history_entry)
            db.session.commit()

    @classmethod
    def get_offers_for_moengage_export(cls):
        """
        Retrieves eligible offers for Moengage export.
        Excludes DND customers and only includes 'Active' offers.
        (FR24: avoid sending offers to DND customers)
        """
        return cls.query.join(Customer).filter(
            cls.offer_status == 'Active',
            Customer.is_dnd == False
        ).all()

    @classmethod
    def get_offers_by_status(cls, status):
        """Retrieves offers by a specific status."""
        return cls.query.filter_by(offer_status=status).all()

    @classmethod
    def get_offers_by_type(cls, offer_type):
        """Retrieves offers by a specific type."""
        return cls.query.filter_by(offer_type=offer_type).all()

    # This method is typically handled by querying the OfferHistory model directly
    # or through a dedicated service layer.
    # @classmethod
    # def get_offer_history_for_offer(cls, offer_id):
    #     """Retrieves offer history entries for a given offer ID."""
    #     return OfferHistory.query.filter_by(offer_id=offer_id).order_by(OfferHistory.status_change_date.desc()).all()