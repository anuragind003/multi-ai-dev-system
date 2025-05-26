import sqlite3
import uuid

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    """
    Establishes a database connection or returns the existing one for the current request.
    The connection is stored in Flask's `g` object to ensure it's reused within the same request.
    `sqlite3.Row` is used as the row factory to allow dictionary-like access to query results.
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
    Closes the database connection if it exists in Flask's `g` object.
    This function is registered as a teardown function for the Flask application context,
    ensuring the database connection is closed at the end of each request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """
    Initializes the database by executing the schema.sql script.
    This creates the necessary tables (e.g., 'products') if they don't exist.
    """
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """
    A Flask CLI command to initialize the database.
    Usage: `flask init-db`
    This command will clear any existing data and create new tables based on `schema.sql`.
    """
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    """
    Registers database-related functions with the Flask application instance.
    - `close_db` is registered as a teardown function.
    - `init_db_command` is added to the Flask CLI.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


# --- CRUD Operations for Products ---

def create_product(name, description, price, stock_quantity):
    """
    Inserts a new product into the database.
    A unique ID (UUID) is automatically generated for the product.
    Returns the dictionary representation of the newly created product.
    """
    db = get_db()
    product_id = str(uuid.uuid4())
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
        (product_id, name, description, price, stock_quantity)
    )
    db.commit()
    return {
        "id": product_id,
        "name": name,
        "description": description,
        "price": price,
        "stock_quantity": stock_quantity
    }


def get_all_products():
    """
    Retrieves all products from the database.
    Returns a list of dictionaries, where each dictionary represents a product.
    """
    db = get_db()
    products = db.execute(
        "SELECT id, name, description, price, stock_quantity FROM products"
    ).fetchall()
    return [dict(product) for product in products]


def get_product_by_id(product_id):
    """
    Retrieves a single product by its unique ID.
    Returns a dictionary representing the product if found, otherwise None.
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
    Only the fields present in the `data` dictionary will be updated.
    Returns the dictionary representation of the updated product if found, otherwise None.
    """
    db = get_db()
    current_product = get_product_by_id(product_id)
    if not current_product:
        return None

    set_clauses = []
    params = []
    # Iterate through allowed updateable fields and build query dynamically
    for key, value in data.items():
        if key in ["name", "description", "price", "stock_quantity"]:
            set_clauses.append(f"{key} = ?")
            params.append(value)

    if not set_clauses:
        # No valid fields provided for update, return current product state
        return current_product

    params.append(product_id)  # Add product_id for the WHERE clause

    query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?"
    cursor = db.cursor()
    cursor.execute(query, tuple(params))
    db.commit()

    # Fetch and return the updated product to confirm changes
    return get_product_by_id(product_id)


def delete_product(product_id):
    """
    Deletes a product from the database by its ID.
    Returns True if the product was successfully deleted, False if not found.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    # Check if any row was actually deleted
    return cursor.rowcount > 0