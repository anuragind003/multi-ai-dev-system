from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    """
    Represents a user in the Simple Task Tracker application.

    This model defines the structure for storing user information,
    including authentication credentials (email and hashed password)
    and timestamps for creation and last update. It also establishes
    a relationship with the Task model, indicating tasks created by this user.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = db.relationship('Task', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        """
        Hashes the provided plain-text password using a secure hashing algorithm
        (e.g., PBKDF2 with SHA256, as used by werkzeug.security by default)
        and stores the hash in the 'password_hash' field.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verifies if the provided plain-text password matches the stored
        hashed password. This method uses the same hashing algorithm
        to hash the input password and then compares it with the stored hash.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        """
        Returns a string representation of the User object, useful for debugging
        and logging purposes.
        """
        return f'<User {self.email}>'