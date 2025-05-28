from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize SQLAlchemy
db = SQLAlchemy()

def create_app():
    """
    Creates and configures the Flask application.
    """
    app = Flask(__name__)

    # Load configuration from environment variables or a default for development
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://cdp_user:cdp_password@localhost:5432/cdp_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_super_secret_key_here') # Replace with a strong secret key in production

    # Initialize extensions
    db.init_app(app)

    # Import and register blueprints
    from .routes.ingestion import ingestion_bp
    from .routes.events import events_bp
    from .routes.customers import customers_bp
    from .routes.exports import exports_bp

    app.register_blueprint(ingestion_bp, url_prefix='/ingest')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(exports_bp, url_prefix='/exports')

    # Optional: A simple health check endpoint
    @app.route('/health')
    def health_check():
        """
        Health check endpoint to verify the application is running.
        """
        return {'status': 'ok', 'message': 'CDP Backend is running'}

    return app