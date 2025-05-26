import sqlite3
import uuid
from flask import Blueprint, request, jsonify, g, current_app

# Create a Blueprint for product routes
products_bp = Blueprint('products', __name__, url_prefix='/products')

# Define the database path. In a larger app, this would be in a config file.
DATABASE = 'database.db'

def get_db():
    """
    Establishes a database connection if one is not already present for the current request.
    The connection is stored in Flask's `g` object.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES # This helps with type conversion for dates/times if used
        )
        g.db.row_factory = sqlite3.Row # This allows accessing columns by name
    return g.db

@products_bp.teardown_request
def close_db(exception):
    """
    Closes the database connection at the end of the request.
    This function is registered with the blueprint's teardown_request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def row_to_dict(row):
    """
    Converts a sqlite3.Row object to a standard Python dictionary.
    This is useful for jsonify responses.
    """
    return dict(row)

@products_bp.route('/', methods=['POST'])
def create_product():
    """
    API endpoint to create a new product.
    Requires 'name', 'price', 'stock_quantity' in the JSON request body.
    'description' is optional.
    Returns the newly created product with a 201 status code on success.
    Handles 400 Bad Request for invalid input.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    name = data.get('name')
    price = data.get('price')
    stock_quantity = data.get('stock_quantity')
    description = data.get('description')

    # Validate required fields
    if not name or not isinstance(name, str):
        return jsonify({"error": "Product name (string) is required"}), 400
    if price is None:
        return jsonify({"error": "Product price is required"}), 400
    if stock_quantity is None:
        return jsonify({"error": "Product stock_quantity is required"}), 400

    # Validate data types and constraints
    try:
        price = float(price)
        if price < 0:
            return jsonify({"error": "Price must be a non-negative number"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Price must be a valid number"}), 400

    try:
        stock_quantity = int(stock_quantity)
        if stock_quantity < 0:
            return jsonify({"error": "Stock quantity must be a non-negative integer"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Stock quantity must be a valid integer"}), 400

    if description is not None and not isinstance(description, str):
        return jsonify({"error": "Description must be a string or null"}), 400

    product_id = str(uuid.uuid4()) # Generate a unique ID

    db = get_db()
    try:
        db.execute(
            "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (product_id, name, description, price, stock_quantity)
        )
        db.commit()
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error during product creation: {e}")
        return jsonify({"error": "Failed to create product due to database error"}), 500

    new_product = {
        "id": product_id,
        "name": name,
        "description": description,
        "price": price,
        "stock_quantity": stock_quantity
    }
    return jsonify(new_product), 201

@products_bp.route('/', methods=['GET'])
def get_all_products():
    """
    API endpoint to retrieve a list of all products.
    Returns a JSON array of product objects.
    """
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    return jsonify([row_to_dict(product) for product in products]), 200

@products_bp.route('/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    """
    API endpoint to retrieve details for a specific product by its ID.
    Returns the product object if found, or 404 Not Found.
    """
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(row_to_dict(product)), 200

@products_bp.route('/<string:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    API endpoint to update an existing product's details.
    Supports partial updates: only fields provided in the JSON body will be updated.
    Returns the updated product object if successful, or 404 Not Found/400 Bad Request.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if product is None:
        return jsonify({"error": "Product not found"}), 404

    # Convert product row to dict for easier modification and to build the response
    updated_product_data = row_to_dict(product)

    # Prepare for dynamic update query
    update_fields = []
    update_values = []

    # Check and update fields if provided in the request body
    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name']:
            return jsonify({"error": "Name must be a non-empty string"}), 400
        update_fields.append("name = ?")
        update_values.append(data['name'])
        updated_product_data['name'] = data['name']

    if 'description' in data:
        # Description can be null, so check for string or None
        if not isinstance(data['description'], (str, type(None))):
            return jsonify({"error": "Description must be a string or null"}), 400
        update_fields.append("description = ?")
        update_values.append(data['description'])
        updated_product_data['description'] = data['description']

    if 'price' in data:
        try:
            price = float(data['price'])
            if price < 0:
                return jsonify({"error": "Price must be a non-negative number"}), 400
            update_fields.append("price = ?")
            update_values.append(price)
            updated_product_data['price'] = price
        except (ValueError, TypeError):
            return jsonify({"error": "Price must be a valid number"}), 400

    if 'stock_quantity' in data:
        try:
            stock_quantity = int(data['stock_quantity'])
            if stock_quantity < 0:
                return jsonify({"error": "Stock quantity must be a non-negative integer"}), 400
            update_fields.append("stock_quantity = ?")
            update_values.append(stock_quantity)
            updated_product_data['stock_quantity'] = stock_quantity
        except (ValueError, TypeError):
            return jsonify({"error": "Stock quantity must be a valid integer"}), 400

    # If no valid fields were provided for update, return 200 with current data
    if not update_fields:
        return jsonify({"message": "No valid fields provided for update, product remains unchanged",
                        "product": updated_product_data}), 200

    update_query = "UPDATE products SET " + ", ".join(update_fields) + " WHERE id = ?"
    update_values.append(product_id)

    try:
        db.execute(update_query, tuple(update_values))
        db.commit()
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error during product update: {e}")
        return jsonify({"error": "Failed to update product due to database error"}), 500

    return jsonify(updated_product_data), 200

@products_bp.route('/<string:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    API endpoint to remove a product from the system by its ID.
    Returns a success message with 200 status, or 404 Not Found.
    """
    db = get_db()
    cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"message": "Product deleted successfully"}), 200