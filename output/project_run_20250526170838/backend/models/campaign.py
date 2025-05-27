from datetime import datetime
import uuid
from backend.app import db  # Assuming db is initialized in backend/app.py or similar


class CampaignMetrics(db.Model):
    """
    Represents campaign metrics stored in the database.
    Corresponds to the 'campaign_metrics' table in the database schema.
    """
    __tablename__ = 'campaign_metrics'

    metric_id = db.Column(db.String(36), primary_key=True,
                          default=lambda: str(uuid.uuid4()))
    campaign_unique_id = db.Column(db.String(255), unique=True, nullable=False)
    campaign_name = db.Column(db.String(255))
    campaign_date = db.Column(db.Date)
    attempted_count = db.Column(db.Integer)
    sent_success_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    conversion_rate = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    def __init__(self, campaign_unique_id, campaign_name, campaign_date,
                 attempted_count=0, sent_success_count=0, failed_count=0,
                 conversion_rate=0.0):
        self.campaign_unique_id = campaign_unique_id
        self.campaign_name = campaign_name
        self.campaign_date = campaign_date
        self.attempted_count = attempted_count
        self.sent_success_count = sent_success_count
        self.failed_count = failed_count
        self.conversion_rate = conversion_rate

    def __repr__(self):
        return (f"<CampaignMetrics(campaign_unique_id='{self.campaign_unique_id}', "
                f"campaign_name='{self.campaign_name}', "
                f"campaign_date='{self.campaign_date}')>")

    def to_dict(self):
        """
        Converts the CampaignMetrics object to a dictionary for JSON serialization.
        """
        return {
            'metric_id': self.metric_id,
            'campaign_unique_id': self.campaign_unique_id,
            'campaign_name': self.campaign_name,
            'campaign_date': self.campaign_date.isoformat()
            if self.campaign_date else None,
            'attempted_count': self.attempted_count,
            'sent_success_count': self.sent_success_count,
            'failed_count': self.failed_count,
            'conversion_rate': float(self.conversion_rate)
            if self.conversion_rate is not None else None,
            'created_at': self.created_at.isoformat()
            if self.created_at else None
        }

    @classmethod
    def create(cls, campaign_unique_id, campaign_name, campaign_date,
               attempted_count=0, sent_success_count=0, failed_count=0,
               conversion_rate=0.0):
        """
        Creates a new CampaignMetrics record and adds it to the session.
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
    def get_by_campaign_id(cls, campaign_unique_id):
        """
        Retrieves a CampaignMetrics record by its unique campaign ID.
        """
        return cls.query.filter_by(campaign_unique_id=campaign_unique_id).first()

    def update(self, **kwargs):
        """
        Updates an existing CampaignMetrics record.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()

    def delete(self):
        """
        Deletes the CampaignMetrics record from the database.
        """
        db.session.delete(self)
        db.session.commit()