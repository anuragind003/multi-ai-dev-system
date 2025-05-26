import sqlite3
import uuid
from flask import g, current_app

def get_db():
    """
    Establishes a database connection for the current request context
    or returns an existing one.
    The connection is stored in Flask's `g` object.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # Configure row_factory to return rows that behave like dictionaries
        # This allows accessing columns by name (e.g., row['name'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """
    Closes the database connection if it exists in the current request context.
    This function is registered as a teardown function for the application context.
    """
    db = g.pop('db', None) # Safely remove 'db' from g
    if db is not None:
        db.close()

def init_db():
    """
    Initializes the database schema by executing SQL commands from a schema file.
    This function should be called once, typically during application setup or via a CLI command.
    It assumes a 'schema.sql' file exists in the application's instance folder or root.
    """
    db = get_db()
    # current_app.open_resource opens a file relative to the application's root path
    with current_app.open_resource('schema.sql', mode='r') as f:
        db.executescript(f.read())
    db.commit() # Commit the schema creation

def init_app(app):
    """
    Registers the database teardown function with the Flask application.
    This ensures that the database connection is closed automatically
    at the end of each request.
    """
    app.teardown_appcontext(close_db)
    # If a CLI command for init_db is desired, it would be registered here too.
    # For this file, just the teardown is sufficient.

def generate_uuid():
    """
    Generates a unique identifier (UUID) as a string.
    Used for product IDs.
    """
    return str(uuid.uuid4())

def validate_product_data(data, is_partial_update=False):
    """
    Validates product data for creation or update operations.

    Args:
        data (dict): The product data to validate.
        is_partial_update (bool): True if this is a partial update (PUT),
                                   False if it's a full creation (POST).

    Returns:
        tuple: A tuple containing (is_valid, errors_list).
               is_valid (bool): True if data is valid, False otherwise.
               errors_list (list): A list of error messages if validation fails.
    """
    errors = []

    # --- Validation for required fields during creation ---
    if not is_partial_update:
        if 'name' not in data or not isinstance(data['name'], str) or not data['name'].strip():
            errors.append("Product name is required and cannot be empty.")
        if 'price' not in data:
            errors.append("Product price is required.")
        if 'stock_quantity' not in data:
            errors.append("Product stock quantity is required.")

    # --- Validation for specific field types and values (for both create and update) ---

    # Name validation
    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name'].strip():
            errors.append("Product name cannot be empty.")

    # Description validation (optional field, but if present, should be string)
    if 'description' in data and not isinstance(data['description'], str):
        errors.append("Product description must be a string.")

    # Price validation
    if 'price' in data:
        try:
            price = float(data['price'])
            if price <= 0:
                errors.append("Product price must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Product price must be a valid number.")

    # Stock quantity validation
    if 'stock_quantity' in data:
        try:
            stock_quantity = int(data['stock_quantity'])
            if stock_quantity < 0:
                errors.append("Product stock quantity cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Product stock quantity must be a valid integer.")

    return len(errors) == 0, errors