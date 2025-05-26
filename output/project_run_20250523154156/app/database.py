import sqlite3
import uuid
from flask import g, current_app

def get_db_connection():
    """
    Establishes a connection to the SQLite database.
    Uses Flask's `g` object to store the connection for the current request context,
    ensuring it's reused and closed properly at the end of the request.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # Configure row_factory to return rows that behave like dictionaries,
        # allowing access by column name.
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """
    Closes the database connection if it exists in the current application context.
    This function is registered with Flask's `teardown_appcontext` to be called
    automatically after each request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initializes the database by creating the 'products' table if it doesn't already exist.
    The schema is based on the project's system design.
    """
    db = get_db_connection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL
        );
    """)
    db.commit()
    current_app.logger.info("Database initialized: 'products' table ensured.")

def init_app(app):
    """
    Registers database functions with the Flask application.
    - `close_db` is registered as a teardown function to ensure connections are closed.
    - `init_db` is not called directly here but is expected to be called
      via a CLI command or at application startup in `app.py`.
    """
    app.teardown_appcontext(close_db)

# --- CRUD Operations for Products ---

def create_product(name, description, price, stock_quantity):
    """
    Inserts a new product into the database with a generated UUID.
    Returns the dictionary representation of the newly created product.
    Raises sqlite3.Error on database operation failure.
    """
    db = get_db_connection()
    product_id = str(uuid.uuid4())
    try:
        db.execute(
            "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (product_id, name, description, price, stock_quantity)
        )
        db.commit()
        current_app.logger.info(f"Product created: {product_id}")
        return {
            "id": product_id,
            "name": name,
            "description": description,
            "price": price,
            "stock_quantity": stock_quantity
        }
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error creating product: {e}")
        db.rollback()
        raise # Re-raise the exception for higher-level handling

def get_all_products():
    """
    Retrieves all products from the database.
    Returns a list of dictionaries, each representing a product.
    """
    db = get_db_connection()
    cursor = db.execute("SELECT id, name, description, price, stock_quantity FROM products")
    products = cursor.fetchall()
    current_app.logger.debug(f"Retrieved {len(products)} products.")
    return [dict(row) for row in products]

def get_product_by_id(product_id):
    """
    Retrieves a single product by its ID.
    Returns a dictionary representing the product, or None if not found.
    """
    db = get_db_connection()
    cursor = db.execute(
        "SELECT id, name, description, price, stock_quantity FROM products WHERE id = ?",
        (product_id,)
    )
    product = cursor.fetchone()
    if product:
        current_app.logger.debug(f"Retrieved product: {product_id}")
        return dict(product)
    current_app.logger.debug(f"Product not found: {product_id}")
    return None

def update_product(product_id, data):
    """
    Updates an existing product's details. Supports partial updates by only
    modifying fields present in the `data` dictionary.
    Returns the dictionary representation of the updated product, or None if
    the product was not found. Raises sqlite3.Error on database operation failure.
    """
    db = get_db_connection()
    set_clauses = []
    params = []

    # Dynamically build the SET clause based on provided data
    if 'name' in data:
        set_clauses.append("name = ?")
        params.append(data['name'])
    if 'description' in data:
        set_clauses.append("description = ?")
        params.append(data['description'])
    if 'price' in data:
        set_clauses.append("price = ?")
        params.append(data['price'])
    if 'stock_quantity' in data:
        set_clauses.append("stock_quantity = ?")
        params.append(data['stock_quantity'])

    if not set_clauses:
        current_app.logger.warning(f"No fields provided for update for product: {product_id}. Returning current state.")
        # If no fields are provided for update, return the current product state if it exists.
        return get_product_by_id(product_id)

    query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?"
    params.append(product_id) # Add product_id to the parameters for the WHERE clause

    try:
        cursor = db.execute(query, tuple(params))
        db.commit()
        if cursor.rowcount == 0:
            current_app.logger.info(f"Product not found for update: {product_id}")
            return None # Product not found
        current_app.logger.info(f"Product updated: {product_id}")
        return get_product_by_id(product_id) # Return the updated product data
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error updating product {product_id}: {e}")
        db.rollback()
        raise

def delete_product(product_id):
    """
    Deletes a product from the database by its ID.
    Returns True if the product was deleted, False otherwise (e.g., product not found).
    Raises sqlite3.Error on database operation failure.
    """
    db = get_db_connection()
    try:
        cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()
        if cursor.rowcount > 0:
            current_app.logger.info(f"Product deleted: {product_id}")
            return True # Product was deleted
        current_app.logger.info(f"Product not found for deletion: {product_id}")
        return False # Product not found
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error deleting product {product_id}: {e}")
        db.rollback()
        raise