import sqlite3
import uuid
from flask import Flask, request, jsonify, g

# Configuration
DATABASE = 'products.db'
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)

def get_db():
    """Establishes a database connection or returns the existing one."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row  # This allows accessing columns by name
    return g.db

def close_db(e=None):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database schema."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock_quantity INTEGER NOT NULL
            );
        """)
        db.commit()

# Register the close_db function to be called after each request
app.teardown_appcontext(close_db)

# Initialize the database when the application starts
with app.app_context():
    init_db()

# Helper function to convert a Row object to a dictionary
def product_to_dict(product_row):
    if product_row is None:
        return None
    return {
        "id": product_row["id"],
        "name": product_row["name"],
        "description": product_row["description"],
        "price": float(product_row["price"]),  # Ensure price is float
        "stock_quantity": int(product_row["stock_quantity"]) # Ensure stock_quantity is int
    }

# Error Handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": str(error)}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method Not Allowed", "message": str(error)}), 405

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500

# API Endpoints

@app.route('/products', methods=['POST'])
def create_product():
    """
    Creates a new product.
    Requires: name (string), price (float), stock_quantity (integer).
    Optional: description (string).
    """
    data = request.get_json()
    if not data:
        return bad_request("Request body must be JSON.")

    name = data.get('name')
    price = data.get('price')
    stock_quantity = data.get('stock_quantity')
    description = data.get('description')

    if not all([name, price is not None, stock_quantity is not None]):
        return bad_request("Missing required fields: 'name', 'price', and 'stock_quantity'.")

    try:
        price = float(price)
        stock_quantity = int(stock_quantity)
        if price < 0 or stock_quantity < 0:
            return bad_request("Price and stock_quantity must be non-negative.")
    except (ValueError, TypeError):
        return bad_request("Invalid data types for 'price' (float) or 'stock_quantity' (integer).")

    product_id = str(uuid.uuid4())

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (product_id, name, description, price, stock_quantity)
        )
        db.commit()

        # Retrieve the newly created product to return it
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        new_product = cursor.fetchone()
        return jsonify(product_to_dict(new_product)), 201
    except sqlite3.Error as e:
        db.rollback()
        return internal_server_error(f"Database error: {e}")

@app.route('/products', methods=['GET'])
def get_all_products():
    """Retrieves a list of all products."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return jsonify([product_to_dict(p) for p in products]), 200

@app.route('/products/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    """Retrieves details for a specific product by its unique ID."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()

    if product is None:
        return not_found(f"Product with ID '{product_id}' not found.")
    
    return jsonify(product_to_dict(product)), 200

@app.route('/products/<string:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Modifies an existing product's details by ID, supporting partial updates.
    Fields that can be updated: name (string), description (string), price (float), stock_quantity (integer).
    """
    data = request.get_json()
    if not data:
        return bad_request("Request body must be JSON.")

    db = get_db()
    cursor = db.cursor()

    # Check if product exists
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    existing_product = cursor.fetchone()
    if existing_product is None:
        return not_found(f"Product with ID '{product_id}' not found.")

    update_fields = []
    update_values = []

    # Dynamically build the update query for partial updates
    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name'].strip():
            return bad_request("Name must be a non-empty string.")
        update_fields.append("name = ?")
        update_values.append(data['name'])
    if 'description' in data:
        if not isinstance(data['description'], (str, type(None))):
            return bad_request("Description must be a string or null.")
        update_fields.append("description = ?")
        update_values.append(data['description'])
    if 'price' in data:
        try:
            price = float(data['price'])
            if price < 0:
                return bad_request("Price must be non-negative.")
            update_fields.append("price = ?")
            update_values.append(price)
        except (ValueError, TypeError):
            return bad_request("Invalid data type for 'price' (float).")
    if 'stock_quantity' in data:
        try:
            stock_quantity = int(data['stock_quantity'])
            if stock_quantity < 0:
                return bad_request("Stock quantity must be non-negative.")
            update_fields.append("stock_quantity = ?")
            update_values.append(stock_quantity)
        except (ValueError, TypeError):
            return bad_request("Invalid data type for 'stock_quantity' (integer).")

    if not update_fields:
        return bad_request("No valid fields provided for update.")

    update_query = "UPDATE products SET " + ", ".join(update_fields) + " WHERE id = ?"
    update_values.append(product_id)

    try:
        cursor.execute(update_query, tuple(update_values))
        db.commit()

        # Retrieve the updated product to return it
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        updated_product = cursor.fetchone()
        return jsonify(product_to_dict(updated_product)), 200
    except sqlite3.Error as e:
        db.rollback()
        return internal_server_error(f"Database error: {e}")

@app.route('/products/<string:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Removes a product from the system using its ID."""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()

        if cursor.rowcount == 0:
            return not_found(f"Product with ID '{product_id}' not found.")
        
        return jsonify({"message": "Product deleted successfully."}), 200
    except sqlite3.Error as e:
        db.rollback()
        return internal_server_error(f"Database error: {e}")

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])