import os
import sys

# Determine the project root (directory containing this wsgi.py).
# This is typically the 'backend' directory.
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the project root to the Python path.
# This allows WSGI servers to locate and import the Flask application module (e.g., 'app.py').
sys.path.insert(0, current_dir)

# Import the Flask application instance.
# The main Flask app object is assumed to be in 'app.py' and named 'app'.
# WSGI servers expect the entry point to be named 'application'.
from app import app as application

# The 'application' variable is the standard WSGI entry point.
# This file bridges the WSGI server (e.g., Gunicorn, uWSGI) and your Flask application.