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

    # Load configuration from environment variables or a config file
    # For production, use a more robust config management (e.g., Flask-DotEnv, separate config classes)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_only_change_this_in_prod')
    app.config['JSON_SORT_KEYS'] = False # Keep JSON output order consistent

    # Initialize extensions with the app
    db.init_app(app)
    CORS(app) # Enable CORS for frontend integration

    # Import and register blueprints
    # These imports assume that ingestion.py, events.py, etc., are in the same 'routes' package
    # and define their own blueprints (e.g., ingestion_bp = Blueprint('ingestion', __name__)).
    # The 'url_prefix' ensures all routes in that blueprint are prefixed, e.g., /api/ingest/e-aggregator-data
    try:
        from .ingestion import ingestion_bp
        from .events import events_bp
        from .exports import exports_bp
        from .customers import customers_bp

        app.register_blueprint(ingestion_bp, url_prefix='/api')
        app.register_blueprint(events_bp, url_prefix='/api')
        app.register_blueprint(exports_bp, url_prefix='/api')
        app.register_blueprint(customers_bp, url_prefix='/api')
    except ImportError as e:
        print(f"Error importing blueprints: {e}. Ensure all route files exist and define their blueprints.")
        # Depending on the severity, you might want to raise the exception or handle it differently.

    # A simple root route for testing the API status
    @app.route('/api/status')
    def api_status():
        """Returns the status of the CDP Backend API."""
        return {'status': 'CDP Backend API is running', 'version': '1.0'}

    # Ensure database tables are created within the application context
    # This is suitable for development and initial setup. For production, use Flask-Migrate or Alembic
    # for proper database migrations.
    with app.app_context():
        # For db.create_all() to work, all SQLAlchemy models must be imported
        # and registered with the 'db' instance before this call.
        # If models are in a separate 'backend/models.py' file, they would typically be imported here
        # or in a central place that is imported by this file.
        # Example: from ..models import Customer, Offer, OfferHistory, Event, Campaign
        try:
            db.create_all()
            print("Database tables created/checked.")
        except Exception as e:
            print(f"Error creating database tables: {e}")
            # In a production environment, this error should be logged and handled appropriately.

    return app