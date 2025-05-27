import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging

# Initialize SQLAlchemy outside the function so it can be imported by models
db = SQLAlchemy()

def create_app():
    """
    Application factory function for the Flask app.
    Initializes the Flask app, loads configuration, sets up the database,
    configures logging, and registers blueprints.
    """
    app = Flask(__name__)

    # --- Configuration ---
    # Load configuration from environment variables for production readiness
    # Provide a default for local development if DATABASE_URL is not set
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/cdp_db' # Default for local development
    )
    # Disable SQLAlchemy event system for tracking modifications, saves memory
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuration for file uploads via Admin Portal
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/cdp_uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB maximum upload size

    # Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        app.logger.info(f"Created upload folder: {app.config['UPLOAD_FOLDER']}")

    # --- Database Initialization ---
    # Initialize the SQLAlchemy instance with the Flask app
    db.init_app(app)

    # --- Logging Configuration ---
    # Set up basic logging to console
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.StreamHandler() # Log to standard output
                        ])
    app.logger.info("Flask application configuration loaded and database initialized.")

    # --- Register Blueprints ---
    # Import blueprints here to avoid circular import issues, as blueprints
    # might depend on 'db' or app.config, which are initialized above.
    from backend.src.api.routes import api_bp
    from backend.src.admin.routes import admin_bp

    # Register the API blueprint with a '/api' URL prefix
    app.register_blueprint(api_bp, url_prefix='/api')
    app.logger.info("API blueprint registered with prefix '/api'.")

    # Register the Admin blueprint with a '/admin' URL prefix
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.logger.info("Admin blueprint registered with prefix '/admin'.")

    # --- CLI Commands (Optional, but useful for database management) ---
    @app.cli.command('init-db')
    def init_db_command():
        """
        CLI command to initialize the database.
        Creates all tables defined in the SQLAlchemy models.
        Usage: flask init-db
        """
        with app.app_context():
            # Import models here to ensure all model classes are loaded
            # and registered with SQLAlchemy's metadata before creating tables.
            from backend.src import models # This imports the models.py file
            db.create_all()
        app.logger.info('Database tables initialized.')

    return app