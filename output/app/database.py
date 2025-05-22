import sqlite3
import uuid
import os

# Define the path for the SQLite database file.
# This assumes the 'instance' directory is a sibling to the 'app' directory,
# which is a common Flask convention for instance-specific files.
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # This is 'app/'
PROJECT_ROOT = os.path.dirname(BASE_DIR) # This is the project root directory
INSTANCE_DIR = os.path.join(PROJECT_ROOT, 'instance')
DATABASE_PATH = os.path.join(INSTANCE_DIR, 'database.db')

def get_db_connection():
    """
    Establishes a connection to the SQLite database.
    Sets row_factory to sqlite3.Row to allow accessing columns by name.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database by creating the 'products' table if it doesn't already exist.
    Ensures the 'instance' directory exists.
    """
    # Ensure the instance directory exists before trying to create the database file
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

def create_product(name: str, description: str, price: float, stock_quantity: int) -> dict | None:
    """
    Creates a new product entry in the database.
    A unique ID (UUID) is automatically generated for the product.
    Returns the created product's details as a dictionary, or None if creation fails.
    """
    product_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)',
            (product_id, name, description, price, stock_quantity)
        )
        conn.commit()
        # Return the newly created product's details
        return get_product_by_id(product_id)
    except sqlite3.Error:
        conn.rollback()
        return None
    finally:
        conn.close()

def get_all_products() -> list[dict]:
    """
    Retrieves a list of all products from the database.
    Returns a list of dictionaries, where each dictionary represents a product.
    """
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    # Convert sqlite3.Row objects to standard dictionaries for easier use (e.g., JSON serialization)
    return [dict(product) for product in products]

def get_product_by_id(product_id: str) -> dict | None:
    """
    Retrieves details for a specific product by its unique ID.
    Returns the product's details as a dictionary, or None if the product is not found.
    """
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    return dict(product) if product else None

def update_product(product_id: str, updates: dict) -> dict | None:
    """
    Modifies an existing product's details by its ID.
    Supports partial updates: only the fields present in the 'updates' dictionary will be modified.
    Returns the updated product's details as a dictionary, or None if the product is not found or update fails.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # First, check if the product exists
    existing_product = get_product_by_id(product_id)
    if not existing_product:
        conn.close()
        return None # Product not found

    set_clauses = []
    params = []
    
    # Define allowed fields to prevent arbitrary column updates
    allowed_fields = ['name', 'description', 'price', 'stock_quantity']

    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            params.append(updates[field])

    if not set_clauses:
        conn.close()
        return existing_product # No valid fields provided for update, return existing product

    params.append(product_id) # Add product_id for the WHERE clause

    query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?"

    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        # Return the updated product's details
        return get_product_by_id(product_id)
    except sqlite3.Error:
        conn.rollback()
        return None
    finally:
        conn.close()

def delete_product(product_id: str) -> bool:
    """
    Removes a product from the system using its ID.
    Returns True if the product was successfully deleted, False otherwise.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        return cursor.rowcount > 0 # True if a row was deleted, False otherwise
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()