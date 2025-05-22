import sqlite3
import uuid
from flask import g, current_app

def get_db():
    """
    Establishes a database connection if one is not already present in the current request context.
    The database path is retrieved from the Flask application's configuration.
    Rows are returned as sqlite3.Row objects, allowing dictionary-like access.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """
    Closes the database connection at the end of a request.
    This function is typically registered with app.teardown_appcontext.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initializes the database schema by executing the SQL script from 'schema.sql'.
    This function should be called once, e.g., during application setup or via a CLI command.
    """
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

def generate_uuid():
    """
    Generates a unique UUID (Universally Unique Identifier) string.
    This is used for product IDs as specified in the system design.
    """
    return str(uuid.uuid4())