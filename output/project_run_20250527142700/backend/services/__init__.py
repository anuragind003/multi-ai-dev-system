import logging

# Configure logging for the services package.
# This allows for specific logging configurations for all modules within the 'services' package.
# The main application logger would typically be configured in the top-level __init__.py or app.py.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# You can add handlers here if you want service-specific logs to go to a different place
# than the main application logs, e.g., a dedicated service log file.
# For now, it will inherit handlers from the root logger if not explicitly added here.
# Example:
# handler = logging.StreamHandler()
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

# No Flask app initialization (create_app) or database connection setup here,
# as this file is for a sub-package within 'backend', not the main application entry point.
# These responsibilities belong to the top-level 'backend/__init__.py' or 'backend/app.py'.

# Individual service modules (e.g., customer_service.py, offer_service.py)
# will be defined in separate files within this 'services' directory.
# They will import necessary components (like the database object) from the main application context.