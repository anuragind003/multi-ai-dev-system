from flask import Flask
from flask_cors import CORS
from app.extensions import db

# Import blueprints from their respective modules within the 'app.routes' package.
# Using absolute imports to ensure robustness regardless of how the app is run,
# and to avoid potential "attempted relative import with no known parent package" errors.
from app.routes.realtime_api import realtime_api_bp
from app.routes.admin import admin_bp
from app.routes.reports import reports_bp
from app.routes.customer import customer_bp
from app.routes.lead_routes import lead_bp # Added based on API design and context from app/api/v1/__init__.py

def create_app():
    """
    Factory function to create and configure the Flask application.
    This function sets up the Flask app, initializes extensions,
    and registers all API blueprints.
    """
    app = Flask(__name__)

    # --- Configuration ---
    # Load configuration from a Config object.
    # Assumes a 'config.py' file exists at the project root with a 'Config' class.
    app.config.from_object('config.Config')

    # --- Initialize Extensions ---
    # Enable CORS for all routes to allow cross-origin requests from the React frontend.
    CORS(app)

    # Initialize the SQLAlchemy database object with the Flask app.
    # The 'db' object is expected to be defined in 'app.extensions'.
    db.init_app(app)

    # --- Register Blueprints (API Routes) ---
    # Blueprints organize routes and other app-related functions into modular components.
    # Registering them here makes their routes available to the application.
    app.register_blueprint(realtime_api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(lead_bp)

    # --- Register Error Handlers (Optional but Recommended) ---
    # Example error handlers can be added here or in a dedicated error handling module.
    # @app.errorhandler(404)
    # def not_found_error(error):
    #     return jsonify({"error": "Resource not found"}), 404

    # @app.errorhandler(500)
    # def internal_error(error):
    #     # Rollback any pending database transactions in case of an internal server error
    #     db.session.rollback()
    #     return jsonify({"error": "Internal server error"}), 500

    return app