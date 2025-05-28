from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# Initialize SQLAlchemy globally so it can be imported by models in other modules
db = SQLAlchemy()

def create_app():
    """
    Creates and configures the Flask application.
    Initializes database, CORS, and registers blueprints for API routes.
    """
    app = Flask(__name__)

    # Load configuration from environment variables or a default for development
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://cdp_user:cdp_password@localhost:5432/cdp_db'
    ).replace('postgres://', 'postgresql://') # SQLAlchemy 1.4+ requires postgresql://

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_only_change_this_in_prod')
    app.config['JSON_SORT_KEYS'] = False # Keep JSON output order consistent

    # Initialize extensions
    db.init_app(app)
    CORS(app) # Enable CORS for frontend integration

    # Import and register blueprints
    # Assuming blueprints are located in a 'routes' subpackage within 'backend/cdp'
    from .routes.ingestion import ingestion_bp
    from .routes.events import events_bp
    from .routes.customers import customers_bp
    from .routes.exports import exports_bp

    app.register_blueprint(ingestion_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(exports_bp)

    return app