import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db # Assuming db is initialized in app/extensions.py

class Campaign(db.Model):
    """
    Represents a campaign in the CDP system.
    Maintains details of targeted customers and campaign metrics.
    Corresponds to the 'campaigns' table in the database schema.

    Functional Requirements Addressed:
    - FR33: The system shall maintain all data related to customers and campaigns in CDP.
    - FR34: Campaign data shall include details of all targeted customers and campaign metrics
            (attempted, successfully sent, failed, success rates, conversion rates,
            date of campaign, campaign unique identifier).
    """
    __tablename__ = 'campaigns'

    campaign_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_unique_identifier = db.Column(db.String(100), unique=True, nullable=False)
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_date = db.Column(db.Date)
    targeted_customers_count = db.Column(db.Integer)
    attempted_count = db.Column(db.Integer)
    successfully_sent_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    success_rate = db.Column(db.Numeric(5, 2))
    conversion_rate = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Campaign {self.campaign_unique_identifier} - {self.campaign_name}>"

    def to_dict(self):
        """
        Converts the Campaign object to a dictionary for serialization.
        """
        return {
            'campaign_id': str(self.campaign_id),
            'campaign_unique_identifier': self.campaign_unique_identifier,
            'campaign_name': self.campaign_name,
            'campaign_date': self.campaign_date.isoformat() if self.campaign_date else None,
            'targeted_customers_count': self.targeted_customers_count,
            'attempted_count': self.attempted_count,
            'successfully_sent_count': self.successfully_sent_count,
            'failed_count': self.failed_count,
            'success_rate': float(self.success_rate) if self.success_rate is not None else None,
            'conversion_rate': float(self.conversion_rate) if self.conversion_rate is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def create(cls, **kwargs):
        """
        Creates a new Campaign record in the database.
        :param kwargs: Dictionary of campaign attributes.
        :return: The created Campaign object.
        """
        campaign = cls(**kwargs)
        db.session.add(campaign)
        db.session.commit()
        return campaign

    @classmethod
    def get_by_id(cls, campaign_id):
        """
        Retrieves a Campaign record by its primary key (campaign_id).
        :param campaign_id: UUID of the campaign.
        :return: Campaign object or None if not found.
        """
        return cls.query.get(campaign_id)

    @classmethod
    def get_by_unique_identifier(cls, unique_identifier):
        """
        Retrieves a Campaign record by its unique identifier.
        :param unique_identifier: The unique identifier string for the campaign.
        :return: Campaign object or None if not found.
        """
        return cls.query.filter_by(campaign_unique_identifier=unique_identifier).first()

    def update(self, **kwargs):
        """
        Updates an existing Campaign record with new data.
        :param kwargs: Dictionary of attributes to update.
        :return: The updated Campaign object.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self

    def delete(self):
        """
        Deletes the current Campaign record from the database.
        """
        db.session.delete(self)
        db.session.commit()