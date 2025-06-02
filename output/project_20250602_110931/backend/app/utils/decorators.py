from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required as flask_jwt_required, get_jwt_identity, get_jwt


def login_required(f):
    """
    A custom decorator that ensures a valid JWT token is present in the request.
    It wraps the standard flask_jwt_extended.jwt_required decorator.

    This decorator handles the authentication check. If a valid token is not
    provided, Flask-JWT-Extended will automatically return a 401 Unauthorized
    response.

    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            # The user's identity (e.g., user ID) can be retrieved using get_jwt_identity()
            current_user_id = get_jwt_identity()
            return jsonify(logged_in_as=current_user_id), 200
    """
    @wraps(f)
    @flask_jwt_required()
    def decorated_function(*args, **kwargs):
        # No additional logic is strictly needed here for basic authentication,
        # as flask_jwt_extended handles the token validation and error responses.
        # The decorated function can then safely access get_jwt_identity().
        return f(*args, **kwargs)
    return decorated_function


def roles_required(allowed_roles):
    """
    A custom decorator that ensures the current user has one of the specified roles.
    This decorator must be used *after* `@login_required` or `@jwt_required`
    because it relies on the JWT claims being available.

    It assumes that user roles are stored as a 'roles' claim within the JWT payload.
    For example, when creating the token, you might include roles like this:
    `create_access_token(identity=user.id, additional_claims={"roles": user.roles})`

    Args:
        allowed_roles (list): A list of roles (strings) that are allowed to access the resource.

    Usage:
        @app.route('/admin_only')
        @login_required
        @roles_required(['admin'])
        def admin_route():
            return jsonify(message="Welcome, admin! You have special access."), 200

        @app.route('/manager_or_admin')
        @login_required
        @roles_required(['manager', 'admin'])
        def manager_or_admin_route():
            return jsonify(message="Welcome, manager or admin!"), 200
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Retrieve the entire JWT payload (claims).
            # This assumes a valid JWT has already been processed by a preceding
            # decorator like `@login_required` or `@flask_jwt_required()`.
            claims = get_jwt()

            # Extract the 'roles' claim from the JWT payload.
            # Default to an empty list if the 'roles' claim is not present.
            user_roles = claims.get('roles', [])

            # Ensure user_roles is iterable (e.g., a list or tuple).
            # If a single role is stored as a string, convert it to a list.
            if isinstance(user_roles, str):
                user_roles = [user_roles]
            elif not isinstance(user_roles, (list, tuple)):
                user_roles = [] # Default to empty if not string, list, or tuple

            # Check if the user possesses at least one of the allowed roles.
            # `any()` returns True if any role in `user_roles` is also in `allowed_roles`.
            if not any(role in user_roles for role in allowed_roles):
                # If no matching role is found, return a 403 Forbidden response.
                return jsonify({"msg": "Access forbidden: Insufficient permissions"}), 403
            
            # If the user has the required role, proceed to execute the decorated function.
            return f(*args, **kwargs)
        return decorated_function
    return decorator