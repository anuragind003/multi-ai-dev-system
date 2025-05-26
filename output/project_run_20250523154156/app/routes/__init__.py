from flask import Flask
from app.database import init_db
from .product_routes import product_bp

def create_app():
    """
    Creates and configures the Flask application.
    This function initializes the database and registers blueprints.
    """
    app = Flask(__name__)

    # Initialize the database
    # This ensures the database schema is created when the app starts.
    # It's good practice to do this within an application context.
    with app.app_context():
        init_db()

    # Register blueprints
    # The product_bp blueprint will handle all product-related API endpoints.
    app.register_blueprint(product_bp)

    return app