from flask_sqlalchemy import SQLAlchemy
import uuid

# Initialize SQLAlchemy. This 'db' object will be bound to a Flask app later.
# In a typical Flask application structure, this 'db' instance might be
# initialized in app/__init__.py or app.py and then imported into models.py.
# For the purpose of providing a complete `app/models.py` file, we define it here.
db = SQLAlchemy()

class Product(db.Model):
    """
    Represents a product in the inventory system.
    Corresponds to the 'products' table in the database.
    """
    __tablename__ = 'products'

    id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        """
        Returns a string representation of the Product object.
        """
        return f"<Product(id='{self.id}', name='{self.name}', price={self.price}, stock={self.stock_quantity})>"

    def to_dict(self):
        """
        Converts the Product object to a dictionary, suitable for JSON serialization.
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock_quantity': self.stock_quantity
        }

    @staticmethod
    def from_dict(data):
        """
        Creates a new Product instance from a dictionary of data.
        This is useful for creating a Product object from incoming request JSON.
        """
        return Product(
            name=data.get('name'),
            description=data.get('description'),
            price=data.get('price'),
            stock_quantity=data.get('stock_quantity')
        )