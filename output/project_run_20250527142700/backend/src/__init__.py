from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# Initialize SQLAlchemy globally so it can be imported by models in other modules.
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
    ).replace('postgres://', 'postgresql://') # Ensure compatibility with SQLAlchemy 1.4+

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_secret_key_for_cdp_project') # Replace with a strong secret key in production
    app.config['JSON_SORT_KEYS'] = False # Keep JSON output order consistent

    # Initialize extensions
    db.init_app(app)
    CORS(app) # Enable CORS for frontend integration

    # Import and register blueprints
    # Assuming routes are defined in sub-packages within 'src/routes'
    from .routes.ingestion import ingestion_bp
    from .routes.events import events_bp
    from .routes.customers import customers_bp
    from .routes.exports import exports_bp

    app.register_blueprint(ingestion_bp, url_prefix='/api/ingest')
    app.register_blueprint(events_bp, url_prefix='/api/events')
    app.register_blueprint(customers_bp, url_prefix='/api/customers')
    app.register_blueprint(exports_bp, url_prefix='/api/exports')

    # Optional: A simple health check route
    @app.route('/api/health')
    def health_check():
        return {"status": "ok", "message": "CDP Backend is running"}

    return app