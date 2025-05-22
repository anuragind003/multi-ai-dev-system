import os

# Determine the base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database configuration
# SQLite database file path. It will be created in the project root directory.
DATABASE_PATH = os.path.join(BASE_DIR, 'products.db')

# Flask application configuration
# A secret key is required for Flask sessions and other security features.
# In a production environment, this should be loaded from an environment variable
# or a secure configuration management system.
SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_and_random_key_for_dev'

# You can add more configuration variables here if needed, e.g.,
# DEBUG = True # Set to False in production
# TESTING = False