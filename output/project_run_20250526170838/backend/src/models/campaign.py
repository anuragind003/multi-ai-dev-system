import uuid
from datetime import datetime
from backend.src.extensions import db # Assuming db is initialized in backend/src/extensions.py

class CampaignMetrics(db.Model):
    """
    Represents the campaign_metrics table in the database.
    Stores metrics related to marketing campaigns.
    """
    __tablename__ = 'campaign_metrics'

    metric_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_unique_id = db.Column(db.Text, unique=True, nullable=False)
    campaign_name = db.Column(db.Text)
    campaign_date = db.Column(db.Date)
    attempted_count = db.Column(db.Integer)
    sent_success_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    conversion_rate = db.Column(db.Numeric(5, 2)) # NUMERIC(5,2) for percentage or rate
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, campaign_unique_id, campaign_name=None, campaign_date=None,
                 attempted_count=None, sent_success_count=None, failed_count=None,
                 conversion_rate=None):
        """
        Initializes a new CampaignMetrics object.
        """
        self.campaign_unique_id = campaign_unique_id
        self.campaign_name = campaign_name
        self.campaign_date = campaign_date
        self.attempted_count = attempted_count
        self.sent_success_count = sent_success_count
        self.failed_count = failed_count
        self.conversion_rate = conversion_rate

    def __repr__(self):
        """
        Returns a string representation of the CampaignMetrics object.
        """
        return f"<CampaignMetrics {self.campaign_unique_id} - {self.campaign_name}>"

    def to_dict(self):
        """
        Converts the CampaignMetrics object to a dictionary, suitable for JSON serialization.
        """
        return {
            "metric_id": self.metric_id,
            "campaign_unique_id": self.campaign_unique_id,
            "campaign_name": self.campaign_name,
            "campaign_date": self.campaign_date.isoformat() if self.campaign_date else None,
            "attempted_count": self.attempted_count,
            "sent_success_count": self.sent_success_count,
            "failed_count": self.failed_count,
            "conversion_rate": float(self.conversion_rate) if self.conversion_rate is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create(cls, campaign_unique_id, campaign_name, campaign_date,
               attempted_count, sent_success_count, failed_count, conversion_rate):
        """
        Creates a new CampaignMetrics record in the database.
        """
        new_metric = cls(
            campaign_unique_id=campaign_unique_id,
            campaign_name=campaign_name,
            campaign_date=campaign_date,
            attempted_count=attempted_count,
            sent_success_count=sent_success_count,
            failed_count=failed_count,
            conversion_rate=conversion_rate
        )
        db.session.add(new_metric)
        db.session.commit()
        return new_metric

    @classmethod
    def get_by_campaign_unique_id(cls, campaign_unique_id):
        """
        Retrieves a CampaignMetrics record by its unique campaign ID.
        """
        return cls.query.filter_by(campaign_unique_id=campaign_unique_id).first()

    @classmethod
    def get_all(cls):
        """
        Retrieves all CampaignMetrics records.
        """
        return cls.query.all()

    def update(self, **kwargs):
        """
        Updates an existing CampaignMetrics record with new data.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self

    def delete(self):
        """
        Deletes a CampaignMetrics record from the database.
        """
        db.session.delete(self)
        db.session.commit()