"""
API Blueprint for the Simple Task Tracker application.

This module defines the 'api_bp' Blueprint, which encapsulates all API-related
routes and functionalities. It also imports specific API modules (auth, tasks)
to register their routes with this blueprint and defines common API error handlers.
"""
from flask import Blueprint, jsonify

# Define the API blueprint.
# This blueprint will encapsulate all API-related routes and functionalities.
# The 'url_prefix' ensures that all routes defined within this blueprint
# will be prefixed with '/api' (e.g., /api/auth/register, /api/tasks).
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import the modules that define the API routes.
# These imports are crucial because they execute the code within 'auth.py'
# and 'tasks.py', which in turn registers the routes (e.g., using @api_bp.route)
# with this 'api_bp' blueprint.
from . import auth
from . import tasks

# API-specific error handlers for consistent JSON responses.
@api_bp.errorhandler(404)
def api_not_found_error(error):
    """
    Custom 404 error handler for API routes.
    Returns a JSON response instead of an HTML page.
    """
    return jsonify({"error": "Not Found", "message": "API endpoint not found"}), 404

@api_bp.errorhandler(400)
def bad_request_error(error):
    """
    Custom 400 error handler for API routes.
    Returns a JSON response for bad requests.
    """
    # Flask's BadRequest exception often populates 'description' with useful info.
    message = getattr(error, 'description', 'Bad request')
    return jsonify({"error": "Bad Request", "message": message}), 400