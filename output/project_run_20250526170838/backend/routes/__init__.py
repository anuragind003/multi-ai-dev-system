from flask import Flask, Blueprint

# Import blueprints from other route files within the same package.
# These files (e.g., api_routes.py, admin_routes.py, data_download_routes.py, report_routes.py)
# are assumed to exist in the same 'backend/routes' directory and define the respective blueprints.
from .api_routes import api_bp
from .admin_routes import admin_bp
from .data_download_routes import data_download_bp
from .report_routes import report_bp


def register_blueprints(app: Flask):
    """
    Registers all application blueprints with the Flask application instance.

    This function is responsible for consolidating and attaching all defined
    API and administrative routes to the main Flask application. Each blueprint
    is registered with a specific URL prefix to organize the API endpoints.

    Args:
        app (Flask): The Flask application instance.
    """
    # Registering blueprints with their respective URL prefixes.
    # The url_prefix ensures that all routes defined within a blueprint
    # will be prefixed with the specified path, e.g., /api/leads, /admin/upload.

    # API Blueprint: Handles real-time data ingestion and status updates.
    # Endpoints: /api/leads, /api/eligibility, /api/status-updates
    app.register_blueprint(api_bp, url_prefix='/api')

    # Admin Blueprint: Handles administrative functionalities like file uploads.
    # Endpoints: /admin/customer-data/upload
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Data Download Blueprint: Handles various data export/download functionalities.
    # Endpoints: /data/duplicates, /data/unique, /data/errors, /data/campaigns/moengage-export
    # Note: The Moengage export is placed here as it's a data export utility.
    app.register_blueprint(data_download_bp, url_prefix='/data')

    # Report Blueprint: Handles reporting and customer-level views.
    # Endpoints: /reports/customers/{customer_id}, /reports/daily-tally (inferred from BRD)
    # Using '/reports' as a general prefix for reporting endpoints.
    app.register_blueprint(report_bp, url_prefix='/reports')