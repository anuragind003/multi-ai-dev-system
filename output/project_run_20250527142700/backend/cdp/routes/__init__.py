from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# Initialize SQLAlchemy globally so it can be imported by models in other modules.
# Assuming models are defined in a central location like `backend/cdp/models.py`
# and will import this `db` object.
db = SQLAlchemy()

def create_app():
    """
    Creates and configures the Flask application.
    Initializes database, CORS, and registers blueprints for API routes.

    This function is placed here based on the interpretation of the project context
    where `backend/routes/__init__.py` (analogous to `backend/cdp/routes/__init__.py`
    in the provided path) contains the `create_app` function in the RAG context,
    and the specific instruction to define `create_app` here if it's the main app package.
    """
    app = Flask(__name__)

    # Load configuration from environment variables or a default for development
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://cdp_user:cdp_password@localhost:5432/cdp_db'
    ).replace('postgres://', 'postgresql://') # SQLAlchemy 1.4+ requires postgresql://

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_only_change_this_in_prod')
    app.config['JSON_SORT_KEYS'] = False # Keep JSON output order consistent for API responses

    # Initialize extensions with the app instance
    db.init_app(app)
    CORS(app) # Enable CORS for frontend integration (Vue.js)

    # Import and register blueprints for different API routes
    # These blueprints are expected to be defined in sibling files within the 'routes' directory
    # e.g., backend/cdp/routes/customer_routes.py, backend/cdp/routes/ingestion_routes.py, etc.
    from .customer_routes import customer_bp
    from .export_routes import export_bp
    from .ingestion_routes import ingestion_bp
    from .event_routes import event_bp

    app.register_blueprint(customer_bp, url_prefix='/api/customers')
    app.register_blueprint(export_bp, url_prefix='/api/exports')
    app.register_blueprint(ingestion_bp, url_prefix='/api/ingest')
    app.register_blueprint(event_bp, url_prefix='/api/events')

    # Basic route for health check or root access
    @app.route('/')
    def index():
        return "LTFS Offer CDP Backend is running!"

    return app