from flask import Blueprint

# Import blueprints from the 'app.routes' package as indicated by the project context.
# This file (app/api/__init__.py) acts as a central point to gather and register
# all API-related blueprints defined in separate modules.
from app.routes.lead_routes import lead_bp
from app.routes.admin import admin_bp
from app.routes.reports import reports_bp # Assuming app/routes/reports.py is the primary reports blueprint

def register_api_blueprints(app):
    """
    Registers all API-related blueprints with the Flask application instance.
    This function is intended to be called from the main application factory
    (e.g., in app.py or app/__init__.py) to organize and load API routes.
    """
    app.register_blueprint(lead_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)