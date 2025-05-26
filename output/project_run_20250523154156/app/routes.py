import sqlite3
import uuid
from flask import Blueprint, request, jsonify, abort, current_app, g

# Create a Blueprint for product routes
products_bp = Blueprint('products', __name__)

def get_db():
    """Establishes a database connection or returns the existing one."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row  # This allows accessing columns by name
    return g.db

@products_bp.teardown_app_request
def close_db(exception):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

@products_bp.errorhandler(400)
def bad_request(error):
    """Handles 400 Bad Request errors."""
    return jsonify({"error": "Bad Request", "message": str(error)}), 400

@products_bp.errorhandler(404)
def not_found(error):
    """Handles 404 Not Found errors."""
    return jsonify({"error": "Not Found", "message": str(error)}), 404

@products_bp.route('/products', methods=['POST'])
def create_product():
    """
    Creates a new product.
    Requires 'name', 'price', 'stock_quantity' in the request body.
    'description' is optional.
    """
    data = request.get_json()

    if not data:
        abort(400, description="Request body must be JSON.")

    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    stock_quantity = data.get('stock_quantity')

    if not all([name, price is not None, stock_quantity is not None]):
        abort(400, description="Missing required fields: name, price, and stock_quantity.")

    if not isinstance(name, str) or not name.strip():
        abort(400, description="Name must be a non-empty string.")
    if not isinstance(price, (int, float)) or price < 0:
        abort(400, description="Price must be a non-negative number.")
    if not isinstance(stock_quantity, int) or stock_quantity < 0:
        abort(400, description="Stock quantity must be a non-negative integer.")
    if description is not None and not isinstance(description, str):
        abort(400, description="Description must be a string or null.")

    product_id = str(uuid.uuid4())
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (product_id, name, description, price, stock_quantity)
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        abort(400, description=f"Database error: {e}")
    except Exception as e:
        abort(500, description=f"An unexpected error occurred: {e}")

    new_product = {
        "id": product_id,
        "name": name,
        "description": description,
        "price": price,
        "stock_quantity": stock_quantity
    }
    return jsonify(new_product), 201

@products_bp.route('/products', methods=['GET'])
def get_all_products():
    """Retrieves a list of all products."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name, description, price, stock_quantity FROM products")
    products = cursor.fetchall()
    return jsonify([dict(row) for row in products])

@products_bp.route('/products/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    """Retrieves details for a specific product using its unique ID."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, name, description, price, stock_quantity FROM products WHERE id = ?",
        (product_id,)
    )
    product = cursor.fetchone()

    if product is None:
        abort(404, description=f"Product with ID '{product_id}' not found.")

    return jsonify(dict(product))

@products_bp.route('/products/<string:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Updates an existing product's details.
    Supports partial updates by only including fields to be modified.
    """
    data = request.get_json()

    if not data:
        abort(400, description="Request body must be JSON.")

    db = get_db()
    cursor = db.cursor()

    # First, check if the product exists
    cursor.execute(
        "SELECT id, name, description, price, stock_quantity FROM products WHERE id = ?",
        (product_id,)
    )
    product = cursor.fetchone()

    if product is None:
        abort(404, description=f"Product with ID '{product_id}' not found.")

    # Build the update query dynamically based on provided fields
    update_fields = []
    update_values = []

    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name'].strip():
            abort(400, description="Name must be a non-empty string.")
        update_fields.append("name = ?")
        update_values.append(data['name'])
    if 'description' in data:
        if data['description'] is not None and not isinstance(data['description'], str):
            abort(400, description="Description must be a string or null.")
        update_fields.append("description = ?")
        update_values.append(data['description'])
    if 'price' in data:
        if not isinstance(data['price'], (int, float)) or data['price'] < 0:
            abort(400, description="Price must be a non-negative number.")
        update_fields.append("price = ?")
        update_values.append(data['price'])
    if 'stock_quantity' in data:
        if not isinstance(data['stock_quantity'], int) or data['stock_quantity'] < 0:
            abort(400, description="Stock quantity must be a non-negative integer.")
        update_fields.append("stock_quantity = ?")
        update_values.append(data['stock_quantity'])

    if not update_fields:
        abort(400, description="No valid fields provided for update.")

    update_query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(product_id)

    try:
        cursor.execute(update_query, tuple(update_values))
        db.commit()
    except sqlite3.IntegrityError as e:
        abort(400, description=f"Database error during update: {e}")
    except Exception as e:
        abort(500, description=f"An unexpected error occurred during update: {e}")

    # Fetch the updated product to return
    cursor.execute(
        "SELECT id, name, description, price, stock_quantity FROM products WHERE id = ?",
        (product_id,)
    )
    updated_product = cursor.fetchone()

    return jsonify(dict(updated_product))

@products_bp.route('/products/<string:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Removes a product from the system using its unique ID."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()

    if cursor.rowcount == 0:
        abort(404, description=f"Product with ID '{product_id}' not found.")

    return jsonify({"message": "Product deleted successfully"}), 200