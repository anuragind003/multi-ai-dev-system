from flask import Flask

# Import application blueprints.
# Blueprints are defined in their respective modules (e.g., auth.py, tasks.py).
from .auth import auth_bp
from .tasks import tasks_bp

def register_blueprints(app: Flask):
    """
    Registers all application blueprints with the Flask application instance.

    This function is designed to be called by the main application factory
    (e.g., in `backend/app/__init__.py`) to attach different sets of routes
    (e.g., authentication, task management) to the Flask application.
    Each blueprint is registered with a URL prefix to organize the API endpoints
    and prevent naming conflicts across different modules.

    Args:
        app (Flask): The Flask application instance to which blueprints will be registered.
    """
    # Register the authentication blueprint.
    # Routes defined within 'auth_bp' will be prefixed with '/auth'.
    # E.g., '/register' in auth.py becomes '/auth/register'.
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Register the tasks management blueprint.
    # Routes defined within 'tasks_bp' will be prefixed with '/tasks'.
    # E.g., '/create' in tasks.py becomes '/tasks/create'.
    app.register_blueprint(tasks_bp, url_prefix='/tasks')

    # Additional blueprints for other functionalities (e.g., user profiles, admin panel)
    # would be imported and registered here as the application grows.