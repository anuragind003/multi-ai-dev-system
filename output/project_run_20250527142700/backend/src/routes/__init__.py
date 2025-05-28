from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# Initialize SQLAlchemy globally so it can be imported by models in other modules.
# This 'db' object will be initialized with the Flask app context in create_app.
db = SQLAlchemy()

def create_app():
    """
    Creates and configures the Flask application.
    Initializes database, CORS, and registers blueprints for API routes.

    This function is placed here based on the interpretation of the project context
    where `backend/src/routes/__init__.py` is considered the main app package
    for the purpose of defining the Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration from environment variables or a default for development
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://cdp_user:cdp_password@localhost:5432/cdp_db'
    ).replace('postgres://', 'postgresql://') # SQLAlchemy 1.4+ requires postgresql://

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'a_very_secret_key_for_development_only_change_this_in_prod'
    )
    app.config['JSON_SORT_KEYS'] = False # Keep JSON output order consistent

    # Initialize extensions
    db.init_app(app)
    CORS(app) # Enable CORS for frontend integration

    # Import and register blueprints
    # Blueprints are defined in separate files within the 'routes' package
    from .ingestion import ingestion_bp
    from .events import events_bp
    from .customers import customers_bp
    from .exports import exports_bp

    app.register_blueprint(ingestion_bp, url_prefix='/api/ingest')
    app.register_blueprint(events_bp, url_prefix='/api/events')
    app.register_blueprint(customers_bp, url_prefix='/api/customers')
    app.register_blueprint(exports_bp, url_prefix='/api/exports')

    return app