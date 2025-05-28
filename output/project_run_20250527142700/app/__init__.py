import os
from flask import Flask
import logging

# Import extensions initialized in app/extensions.py
# This pattern helps avoid circular imports and keeps the app factory clean.
from app.extensions import db, cors

# Import blueprints
# Assuming these blueprints are defined in their respective files
from app.api.v1.admin import admin_bp
from app.routes.report_routes import report_bp

def create_app():
    """
    Flask application factory function.
    Initializes the Flask app, configures extensions, and registers blueprints.
    """
    app = Flask(__name__)

    # --- Configuration ---
    # Load configuration from environment variables or provide defaults
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')
    app.config['LOG_LEVEL'] = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # --- Logging Setup ---
    logging.basicConfig(level=app.config['LOG_LEVEL'],
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app.logger.info(f"Application starting with log level: {app.config['LOG_LEVEL']}")

    # --- Initialize Extensions ---
    # db and cors are initialized in app/extensions.py, then initialized with the app here.
    db.init_app(app)
    cors.init_app(app)

    # --- Register Blueprints ---
    # Register the admin blueprint (e.g., for file uploads)
    app.register_blueprint(admin_bp)
    # Register the reports blueprint (e.g., for file downloads and daily tally)
    app.register_blueprint(report_bp)

    # Note: Core API routes (Lead Generation, Eligibility, Status) are not explicitly
    # defined in a blueprint in the provided RAG context for separate files.
    # They would typically be registered here as well if they were in their own blueprint,
    # e.g., app.register_blueprint(core_api_bp)

    # Ensure database tables are created if running in a development environment.
    # In a production setup, database migrations (e.g., Flask-Migrate) would be used.
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables checked/created.")

    return app