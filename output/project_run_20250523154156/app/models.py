from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

class Product(db.Model):
    """
    Product model representing a product in the inventory.
    Maps to the 'products' table in the database.
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
        return f"<Product {self.id}: {self.name}>"

    def to_dict(self):
        """
        Converts the Product object to a dictionary, suitable for JSON serialization.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock_quantity": self.stock_quantity,
        }