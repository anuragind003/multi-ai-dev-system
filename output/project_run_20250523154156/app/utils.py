import sqlite3
import uuid
import os

DATABASE = 'database.db'

def get_db_connection():
    """
    Establishes a connection to the SQLite database.
    Sets row_factory to sqlite3.Row to allow dictionary-like access to rows.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database by creating the 'products' table if it doesn't exist.
    This function should be called once, typically at application startup.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def generate_uuid():
    """
    Generates a unique identifier (UUID) for product IDs.
    """
    return str(uuid.uuid4())

def validate_product_data(data, is_update=False):
    """
    Validates product data for creation or update.

    Args:
        data (dict): The dictionary containing product data.
        is_update (bool): True if validating for an update (allows partial data), False for creation.

    Returns:
        tuple: A tuple containing (is_valid, error_message).
    """
    required_fields = ['name', 'price', 'stock_quantity']
    errors = []

    if not is_update:
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: '{field}'")
    
    if 'name' in data and not isinstance(data['name'], str):
        errors.append("Name must be a string.")
    elif 'name' in data and not data['name'].strip():
        errors.append("Name cannot be empty.")

    if 'description' in data and not isinstance(data['description'], str):
        errors.append("Description must be a string.")

    if 'price' in data:
        try:
            price = float(data['price'])
            if price <= 0:
                errors.append("Price must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Price must be a valid number.")

    if 'stock_quantity' in data:
        try:
            stock_quantity = int(data['stock_quantity'])
            if stock_quantity < 0:
                errors.append("Stock quantity cannot be negative.")
        except (ValueError, TypeError):
            errors.append("Stock quantity must be a valid integer.")

    if errors:
        return False, ", ".join(errors)
    return True, None

# Ensure the database directory exists if needed (though for single file, not strictly necessary)
# if not os.path.exists(os.path.dirname(DATABASE)):
#     os.makedirs(os.path.dirname(DATABASE))

# Call init_db() when this module is imported to ensure the table exists
# This is a common pattern for simple Flask apps with SQLite.
init_db()