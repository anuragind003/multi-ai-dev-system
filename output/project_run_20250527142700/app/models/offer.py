from app.extensions import db
from datetime import datetime
import uuid # Not strictly needed if using db.func.gen_random_uuid(), but good practice for UUID type handling

class Offer(db.Model):
    """
    SQLAlchemy model for the 'offers' table.
    Manages offer data, including status, type, and linkage to customers.
    """
    __tablename__ = 'offers'

    offer_id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=db.func.gen_random_uuid())
    customer_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.String(20)) # FR16: 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.String(20), default='Active') # FR15: 'Active', 'Inactive', 'Expired'
    propensity_flag = db.Column(db.String(50)) # FR17: e.g., 'dominant tradeline'
    offer_start_date = db.Column(db.Date)
    offer_end_date = db.Column(db.Date)
    loan_application_number = db.Column(db.String(50)) # Nullable, if journey not started (FR13, FR38)
    attribution_channel = db.Column(db.String(50)) # FR20: Channel through which the offer was attributed
    created_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationship to Customer model
    # 'Customer' is assumed to be defined in app/models/customer.py
    customer = db.relationship('Customer', backref=db.backref('offers', lazy=True))

    def __repr__(self):
        return f"<Offer {self.offer_id} | Status: {self.offer_status} | Customer: {self.customer_id}>"

    def to_dict(self):
        """
        Converts the Offer object to a dictionary for easy serialization (e.g., to JSON).
        """
        return {
            'offer_id': str(self.offer_id),
            'customer_id': str(self.customer_id),
            'offer_type': self.offer_type,
            'offer_status': self.offer_status,
            'propensity_flag': self.propensity_flag,
            'offer_start_date': self.offer_start_date.isoformat() if self.offer_start_date else None,
            'offer_end_date': self.offer_end_date.isoformat() if self.offer_end_date else None,
            'loan_application_number': self.loan_application_number,
            'attribution_channel': self.attribution_channel,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def get_by_id(offer_id: uuid.UUID):
        """
        Retrieves an offer by its primary key (offer_id).
        """
        return Offer.query.get(offer_id)

    @staticmethod
    def get_active_offers_for_customer(customer_id: uuid.UUID):
        """
        Retrieves all active offers for a specific customer.
        """
        return Offer.query.filter_by(customer_id=customer_id, offer_status='Active').all()

    @staticmethod
    def create(customer_id: uuid.UUID, offer_data: dict):
        """
        Creates a new offer record in the database.

        Args:
            customer_id (uuid.UUID): The ID of the customer associated with the offer.
            offer_data (dict): A dictionary containing offer details.
                               Expected keys: 'offer_type', 'propensity_flag',
                               'offer_start_date', 'offer_end_date',
                               'loan_application_number', 'attribution_channel'.
                               'offer_status' defaults to 'Active'.
        Returns:
            Offer: The newly created Offer object.
        """
        new_offer = Offer(
            customer_id=customer_id,
            offer_type=offer_data.get('offer_type'),
            offer_status=offer_data.get('offer_status', 'Active'),
            propensity_flag=offer_data.get('propensity_flag'),
            offer_start_date=offer_data.get('offer_start_date'),
            offer_end_date=offer_data.get('offer_end_date'),
            loan_application_number=offer_data.get('loan_application_number'),
            attribution_channel=offer_data.get('attribution_channel')
        )
        db.session.add(new_offer)
        db.session.commit()
        return new_offer

    def update_status(self, new_status: str):
        """
        Updates the status of the current offer.
        """
        if new_status not in ['Active', 'Inactive', 'Expired']:
            raise ValueError("Invalid offer status. Must be 'Active', 'Inactive', or 'Expired'.")
        self.offer_status = new_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def update_details(self, data: dict):
        """
        Updates multiple fields of the current offer based on a dictionary.
        """
        for key, value in data.items():
            if hasattr(self, key) and key not in ['offer_id', 'customer_id', 'created_at']:
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self