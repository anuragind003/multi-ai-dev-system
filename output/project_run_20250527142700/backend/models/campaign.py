import uuid
from datetime import datetime, date
from sqlalchemy.dialects.postgresql import UUID
from backend.extensions import db

class Campaign(db.Model):
    """
    Represents a campaign in the CDP system.
    Corresponds to the 'campaigns' table in the database.
    """
    __tablename__ = 'campaigns'

    campaign_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_date = db.Column(db.Date, nullable=False, default=date.today)
    campaign_unique_identifier = db.Column(db.String(100), unique=True, nullable=False)
    attempted_count = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Numeric(5, 2), default=0.0)
    conversion_rate = db.Column(db.Numeric(5, 2), default=0.0)
    created_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(db.func.timezone('UTC', db.func.now())))
    updated_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(db.func.timezone('UTC', db.func.now())), onupdate=datetime.now(db.func.timezone('UTC', db.func.now())))

    def __repr__(self):
        return f"<Campaign {self.campaign_unique_identifier} - {self.campaign_name}>"

    def to_dict(self):
        """
        Converts the Campaign object to a dictionary for JSON serialization.
        """
        return {
            'campaign_id': str(self.campaign_id),
            'campaign_name': self.campaign_name,
            'campaign_date': self.campaign_date.isoformat() if self.campaign_date else None,
            'campaign_unique_identifier': self.campaign_unique_identifier,
            'attempted_count': self.attempted_count,
            'sent_count': self.sent_count,
            'failed_count': self.failed_count,
            'success_rate': float(self.success_rate) if self.success_rate is not None else 0.0,
            'conversion_rate': float(self.conversion_rate) if self.conversion_rate is not None else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def create(cls, campaign_name, campaign_unique_identifier, campaign_date=None,
               attempted_count=0, sent_count=0, failed_count=0,
               success_rate=0.0, conversion_rate=0.0):
        """
        Creates a new campaign record.
        """
        if campaign_date is None:
            campaign_date = date.today()

        new_campaign = cls(
            campaign_name=campaign_name,
            campaign_date=campaign_date,
            campaign_unique_identifier=campaign_unique_identifier,
            attempted_count=attempted_count,
            sent_count=sent_count,
            failed_count=failed_count,
            success_rate=success_rate,
            conversion_rate=conversion_rate
        )
        db.session.add(new_campaign)
        db.session.commit()
        return new_campaign

    @classmethod
    def get_by_id(cls, campaign_id):
        """
        Retrieves a campaign by its UUID.
        """
        return cls.query.get(campaign_id)

    @classmethod
    def get_by_unique_identifier(cls, identifier):
        """
        Retrieves a campaign by its unique identifier.
        """
        return cls.query.filter_by(campaign_unique_identifier=identifier).first()

    @classmethod
    def get_all_campaigns(cls):
        """
        Retrieves all campaigns.
        """
        return cls.query.all()

    def update(self, **kwargs):
        """
        Updates campaign attributes.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self

    def delete(self):
        """
        Deletes the campaign record.
        """
        db.session.delete(self)
        db.session.commit()

    def calculate_metrics(self):
        """
        Calculates and updates success_rate and conversion_rate based on counts.
        This method assumes that 'sent_count' and 'attempted_count' are updated externally.
        Conversion rate calculation would typically involve events (e.g., EKYC achieved, Disbursement)
        which are not directly part of this model's counts, so this is a placeholder.
        """
        if self.attempted_count > 0:
            self.success_rate = (self.sent_count / self.attempted_count) * 100
        else:
            self.success_rate = 0.0

        # Placeholder for conversion rate calculation.
        # This would typically involve querying the 'events' table for conversion events
        # related to this campaign and dividing by 'sent_count' or 'attempted_count'.
        # For now, it remains as is or can be updated externally.
        # self.conversion_rate = (actual_conversions / self.sent_count) * 100 if self.sent_count > 0 else 0.0

        db.session.commit()