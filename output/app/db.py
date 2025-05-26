import sqlite3
import uuid
import click
from flask import current_app, g

def get_db():
    """
    Establishes a database connection if one doesn't already exist for the current request.
    Stores the connection in Flask's `g` object.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row # Allows accessing columns by name
    return g.db

def close_db(e=None):
    """
    Closes the database connection if it exists.
    This function is typically registered with `app.teardown_appcontext`.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initializes the database by creating the products table based on the schema.
    """
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
def init_db_command():
    """
    CLI command to clear existing data and create new tables.
    """
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    """
    Registers database functions with the Flask application.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

# --- CRUD Operations for Products ---

def create_product(name, description, price, stock_quantity):
    """
    Inserts a new product into the database.
    Generates a unique ID (UUID) for the product.
    Returns the dictionary representation of the created product.
    """
    db = get_db()
    product_id = str(uuid.uuid4()) # Generate a unique ID
    try:
        db.execute(
            "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (product_id, name, description, price, stock_quantity)
        )
        db.commit()
        # Return the newly created product
        return {
            "id": product_id,
            "name": name,
            "description": description,
            "price": price,
            "stock_quantity": stock_quantity
        }
    except sqlite3.IntegrityError:
        # This might happen if a unique constraint was violated, though less likely for UUIDs
        # For simplicity, we'll just return None or re-raise for now.
        # In a real app, more specific error handling would be needed.
        return None

def get_all_products():
    """
    Retrieves all products from the database.
    Returns a list of product dictionaries.
    """
    db = get_db()
    products = db.execute("SELECT id, name, description, price, stock_quantity FROM products").fetchall()
    return [dict(product) for product in products]

def get_product_by_id(product_id):
    """
    Retrieves a single product by its ID.
    Returns a product dictionary if found, None otherwise.
    """
    db = get_db()
    product = db.execute(
        "SELECT id, name, description, price, stock_quantity FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()
    return dict(product) if product else None

def update_product(product_id, data):
    """
    Updates an existing product's details. Supports partial updates.
    Returns the updated product dictionary if successful, None if the product is not found.
    """
    db = get_db()
    set_clauses = []
    values = []

    # Build dynamic SET clause for the UPDATE query
    for key, value in data.items():
        if key in ['name', 'description', 'price', 'stock_quantity']:
            set_clauses.append(f"{key} = ?")
            values.append(value)
    
    if not set_clauses:
        return None # No valid fields to update

    query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?"
    values.append(product_id)

    cursor = db.execute(query, tuple(values))
    db.commit()

    if cursor.rowcount == 0:
        return None # Product not found

    # Retrieve and return the updated product
    return get_product_by_id(product_id)

def delete_product(product_id):
    """
    Deletes a product from the database by its ID.
    Returns True if the product was deleted, False if not found.
    """
    db = get_db()
    cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return cursor.rowcount > 0