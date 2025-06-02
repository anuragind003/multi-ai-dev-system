import os
from app import create_app

"""
This script serves as the entry point for the Flask application.
It initializes the Flask app using an application factory pattern,
configures it based on environment variables, and runs the development server.
"""

# Get the configuration name from an environment variable, defaulting to 'development'.
# This allows easy switching between development, testing, and production configurations.
config_name = os.getenv('FLASK_CONFIG', 'development')

# Get the port number from an environment variable, defaulting to 5000.
# This provides flexibility for deployment environments.
try:
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
except ValueError:
    # Fallback to default if FLASK_RUN_PORT is not a valid integer
    port = 5000
    print("Warning: Invalid FLASK_RUN_PORT environment variable. Defaulting to 5000.")


# Create the Flask application instance using the application factory pattern.
# The factory function `create_app` is responsible for initializing the app,
# configuring it, and registering blueprints.
app = create_app(config_name)

if __name__ == '__main__':
    # Run the Flask development server.
    # In a production environment, a WSGI server like Gunicorn or uWSGI would be used.
    #
    # The debug setting is typically controlled by the configuration loaded by create_app.
    # It should be set to False in production for security and performance reasons.
    #
    # host='0.0.0.0' makes the server accessible from any IP address, not just localhost.
    # This is useful when running in a container or a VM.
    app.run(host='0.0.0.0', port=port)