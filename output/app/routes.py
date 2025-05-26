from flask import Blueprint, request, jsonify, g, current_app
import sqlite3
import uuid

# Define a Blueprint for product routes
bp = Blueprint('products', __name__, url_prefix='/products')

# Database configuration
DATABASE = 'database.db'

def get_db():
    """
    Establishes a database connection for the current request if one is not already present.
    Stores the connection in Flask's `g` object.
    Sets `row_factory` to return rows as dictionaries.
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = make_dicts # Return rows as dictionaries
    return db

def close_db(e=None):
    """
    Closes the database connection at the end of the request.
    This function is registered with `app.teardown_appcontext`.
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initializes the database schema by creating the products table if it doesn't exist.
    This function should be called once, typically during application startup.
    """
    with current_app.app_context():
        db = get_db()
        # Use the schema directly from system design
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

# Helper function to convert SQLite rows to dictionaries
def make_dicts(cursor, row):
    """Converts a SQLite row to a dictionary."""
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

# --- API Endpoints ---

@bp.route('', methods=['POST'])
def create_product():
    """
    FR1: Create Product
    Adds a new product to the system.
    Requires: name (string), price (float), stock_quantity (integer).
    Optional: description (string).
    Returns the created product with a 201 status code.
    Handles 400 for bad requests (missing/invalid data).
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    stock_quantity = data.get('stock_quantity')

    # Input validation based on design notes
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Product name is required and must be a non-empty string"}), 400

    if not isinstance(price, (int, float)) or price <= 0:
        return jsonify({"error": "Product price is required and must be a positive number"}), 400

    if not isinstance(stock_quantity, int) or stock_quantity < 0:
        return jsonify({"error": "Product stock_quantity is required and must be a non-negative integer"}), 400
    
    # Description can be None or an empty string, but if provided, should be a string.
    if description is not None and not isinstance(description, str):
        return jsonify({"error": "Product description must be a string or null"}), 400
    
    product_id = str(uuid.uuid4()) # Generate unique ID (UUID)

    db = get_db()
    try:
        db.execute(
            "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (product_id, name.strip(), description.strip() if description else None, price, stock_quantity)
        )
        db.commit()
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error during product creation: {e}")
        return jsonify({"error": "Failed to create product due to a database error."}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during product creation: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

    new_product = {
        "id": product_id,
        "name": name.strip(),
        "description": description.strip() if description else None,
        "price": price,
        "stock_quantity": stock_quantity
    }
    return jsonify(new_product), 201

@bp.route('', methods=['GET'])
def get_all_products():
    """
    FR2: Get All Products
    Retrieves a list of all products from the system.
    Returns a list of product dictionaries with a 200 status code.
    """
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    return jsonify(products), 200

@bp.route('/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    """
    FR3: Get Product by ID
    Retrieves details for a specific product using its unique ID.
    Returns the product dictionary with a 200 status code if found.
    Returns 404 if the product is not found.
    """
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product), 200

@bp.route('/<string:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    FR4: Update Product
    Modifies an existing product's details using its ID. Supports partial updates.
    Requires: product_id in URL. Request body can contain any of:
    name (string), description (string), price (float), stock_quantity (integer).
    Returns the updated product with a 200 status code.
    Handles 400 for bad requests (invalid data) and 404 if product not found.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    db = get_db()
    # Check if product exists first
    product_exists = db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
    if product_exists is None:
        return jsonify({"error": "Product not found"}), 404

    # Build update query dynamically for partial updates
    updates = []
    params = []

    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name'].strip():
            return jsonify({"error": "Product name must be a non-empty string"}), 400
        updates.append("name = ?")
        params.append(data['name'].strip())
    if 'description' in data:
        # Allow description to be null or empty string
        if data['description'] is not None and not isinstance(data['description'], str):
            return jsonify({"error": "Product description must be a string or null"}), 400
        updates.append("description = ?")
        params.append(data['description'].strip() if data['description'] else None)
    if 'price' in data:
        if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
            return jsonify({"error": "Product price must be a positive number"}), 400
        updates.append("price = ?")
        params.append(data['price'])
    if 'stock_quantity' in data:
        if not isinstance(data['stock_quantity'], int) or data['stock_quantity'] < 0:
            return jsonify({"error": "Product stock_quantity must be a non-negative integer"}), 400
        updates.append("stock_quantity = ?")
        params.append(data['stock_quantity'])

    if not updates:
        return jsonify({"error": "No valid fields provided for update"}), 400

    params.append(product_id) # Add product_id for WHERE clause

    try:
        db.execute(
            f"UPDATE products SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        db.commit()
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error during product update: {e}")
        return jsonify({"error": "Failed to update product due to a database error."}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during product update: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

    # Fetch the updated product to return
    updated_product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify(updated_product), 200

@bp.route('/<string:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    FR5: Delete Product
    Removes a product from the system using its ID.
    Returns 204 No Content if successful.
    Returns 404 if the product is not found.
    """
    db = get_db()
    try:
        cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error during product deletion: {e}")
        return jsonify({"error": "Failed to delete product due to a database error."}), 500
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during product deletion: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

    if cursor.rowcount == 0:
        return jsonify({"error": "Product not found"}), 404
    
    return '', 204 # No Content

def register_routes(app):
    """
    Registers the product blueprint and database teardown function with the Flask app.
    This function should be called from your main application file (e.g., app/__init__.py).
    """
    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)
    # init_db() should be called once during application setup,
    # typically in the main app file after the app instance is created.