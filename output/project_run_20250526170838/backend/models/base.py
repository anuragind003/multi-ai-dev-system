from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

# Initialize SQLAlchemy instance.
# This 'db' object will be initialized with the Flask app later (e.g., in app.py).
db = SQLAlchemy()


class Base(db.Model):
    """
    Base model class providing common columns and utility methods for all other models.
    All application-specific models should inherit from this class.
    """
    __abstract__ = True  # This tells SQLAlchemy not to create a table for this class

    # Common columns for all models, automatically managed by the database.
    # `server_default=func.now()` sets the default value to the current timestamp on creation.
    # `onupdate=func.now()` updates the timestamp whenever the row is modified.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def save(self):
        """
        Saves the current instance to the database.
        Adds the instance to the session and commits the transaction.
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        Deletes the current instance from the database.
        Deletes the instance from the session and commits the transaction.
        """
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, id_value):
        """
        Retrieves an instance of the model by its primary key.
        Assumes the primary key column is named 'id' or can be inferred by SQLAlchemy.
        """
        return cls.query.get(id_value)

    @classmethod
    def get_all(cls):
        """
        Retrieves all instances of the model.
        """
        return cls.query.all()

    def to_dict(self):
        """
        Converts the model instance to a dictionary.
        This method should be overridden by child classes to include specific fields.
        For the base class, it provides common fields.
        """
        return {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }