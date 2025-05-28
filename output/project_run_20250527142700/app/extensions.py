from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Initialize SQLAlchemy
# This object will be initialized with the Flask app instance in app/__init__.py
db = SQLAlchemy()

# Initialize Flask-CORS
# This object will be initialized with the Flask app instance in app/__init__.py
cors = CORS()