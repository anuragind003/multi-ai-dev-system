import os
from flask import Flask

def create_app():
    """
    Creates and configures the Flask application instance.

    This function sets up the Flask application, including:
    - Creating the application instance with instance-relative configuration.
    - Ensuring the instance folder exists for storing database files.
    - Configuring the SQLite database path.
    - Initializing the database connection and schema.
    - Registering the product management blueprint for API routes.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Ensure the instance folder exists
    # This folder is used to store the SQLite database file.
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        # In a production environment, more robust error handling might be needed here,
        # e.g., logging the error or raising a specific exception.
        # For this simple application, exist_ok=True handles most cases.
        pass

    # Configure the database path
    # The database file will be located in the 'instance' folder.
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, 'products.sqlite'),
    )

    # Initialize the database
    # This imports the db module and calls its init_app function
    # to register database-related commands and teardown functions.
    from . import db
    db.init_app(app)

    # Register blueprints
    # This imports the products blueprint and registers it with the app.
    # All routes defined in the products blueprint will be accessible.
    from . import products
    app.register_blueprint(products.bp)

    # A simple test route to verify the app is running
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    return app