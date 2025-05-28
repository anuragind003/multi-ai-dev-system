from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Initialize SQLAlchemy and Migrate globally.
# This allows them to be imported by models and other modules,
# and initialized with the Flask app later in create_app().
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """
    Creates and configures the Flask application.
    Initializes database, migrations, and registers blueprints.
    """
    app = Flask(__name__)

    # Load configuration from backend/config.py
    # Ensure backend.config.Config exists and contains necessary settings
    app.config.from_object('backend.config.Config')

    # Initialize Flask extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints for different API routes
    # These blueprints are expected to be defined in the 'backend/routes' directory
    from backend.routes.customer_routes import customer_bp
    from backend.routes.export_routes import export_bp
    from backend.routes.ingestion_routes import ingestion_bp
    from backend.routes.event_routes import event_bp

    app.register_blueprint(customer_bp, url_prefix='/api/customers')
    app.register_blueprint(export_bp, url_prefix='/api/exports')
    app.register_blueprint(ingestion_bp, url_prefix='/api/ingest')
    app.register_blueprint(event_bp, url_prefix='/api/events')

    # Basic route for health check or root access
    @app.route('/')
    def index():
        return "LTFS Offer CDP Backend is running!"

    return app