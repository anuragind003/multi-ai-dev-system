from .api import api_bp
from .admin import admin_bp
from .reports import reports_bp

def register_blueprints(app):
    """
    Registers all application blueprints with the Flask application instance.

    This function is intended to be called from the main Flask application factory
    (e.g., in `backend/src/__init__.py`) to attach all defined routes.

    Args:
        app (Flask): The Flask application instance.
    """
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)