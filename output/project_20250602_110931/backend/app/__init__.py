import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from typing import Optional, Dict, Any, Tuple

from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """
    Application factory function to create and configure the Flask application.

    This function sets up the Flask app, loads configuration, initializes
    extensions (SQLAlchemy, Bcrypt, JWTManager), registers blueprints,
    and sets up global error handlers.

    Args:
        test_config (dict, optional): A dictionary of configuration overrides for testing.
                                      If provided, these settings will override
                                      the default configuration. Defaults to None.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        app.config.from_object(Config)
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    from app.auth.routes import auth_bp
    from app.tasks.routes import tasks_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tasks_bp, url_prefix='/api')

    @jwt.unauthorized_loader
    def unauthorized_response(_callback: str) -> Tuple[Any, int]:
        """Handler for missing or malformed Authorization header."""
        return jsonify({"msg": "Missing Authorization Header"}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(_callback: str) -> Tuple[Any, int]:
        """Handler for tokens that are invalid (e.g., signature verification failed)."""
        return jsonify({"msg": "Signature verification failed"}), 403

    @jwt.expired_token_loader
    def expired_token_response(_callback: str) -> Tuple[Any, int]:
        """Handler for expired tokens."""
        return jsonify({"msg": "Token has expired"}), 401

    @jwt.revoked_token_loader
    def revoked_token_response(_callback: str) -> Tuple[Any, int]:
        """Handler for tokens that have been explicitly revoked."""
        return jsonify({"msg": "Token has been revoked"}), 401

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_response(_callback: str) -> Tuple[Any, int]:
        """Handler for routes requiring a 'fresh' token when an old one is provided."""
        return jsonify({"msg": "Fresh token required"}), 401

    with app.app_context():
        db.create_all()

    return app