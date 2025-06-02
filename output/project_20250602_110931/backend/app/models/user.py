from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(UserMixin, db.Model):
    """
    SQLAlchemy model for the 'User' entity.

    Defines the structure of the 'users' table in the database,
    including fields for ID, email, and password hash.
    It also includes methods for password management and a relationship
    to the 'Task' model.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Define a one-to-many relationship with the Task model.
    # 'Task' is the name of the related model class.
    # 'backref='user'' adds a 'user' attribute to the Task model,
    # allowing access to the associated User object from a Task.
    # 'lazy=True' means tasks will be loaded only when accessed (e.g., user.tasks).
    # 'cascade='all, delete-orphan'' ensures that if a User is deleted,
    # all associated Tasks are also deleted from the database.
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """
        Hashes the provided plain-text password and stores it in the
        'password_hash' column.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Checks if the provided plain-text password matches the stored hash.
        Returns True if they match, False otherwise.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """
        Returns a string representation of the User object, useful for debugging.
        """
        return f'<User {self.email}>'

    # Flask-Login integration:
    # The UserMixin provides default implementations for is_authenticated,
    # is_active, is_anonymous, and get_id().
    # Our 'id' column serves as the unique identifier for get_id().