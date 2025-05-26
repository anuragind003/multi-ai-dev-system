import sqlite3
import uuid
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = 'database.db'

# Helper function to get a database connection
def get_db_connection():
    conn = getattr(g, '_database', None)
    if conn is None:
        conn = g._database = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

# Close the database connection at the end of the request
@app.teardown_appcontext
def close_connection(exception):
    conn = getattr(g, '_database', None)
    if conn is not None:
        conn.close()

# Initialize the database schema
def init_db():
    with app.app_context():
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

# Call init_db when the application starts
init_db()

# Helper to convert a sqlite3.Row object to a dictionary
def row_to_dict(row):
    return dict(row)

# --- API Endpoints ---

@app.route('/products', methods=['POST'])
def create_product():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    name = data.get('name')
    description = data.get('description')
    price = data.get('price')
    stock_quantity = data.get('stock_quantity')

    # Input validation
    if not name or not isinstance(name, str) or name.strip() == "":
        return jsonify({"error": "Product name is required and must be a non-empty string"}), 400
    if not isinstance(price, (int, float)) or price <= 0:
        return jsonify({"error": "Price is required and must be a positive number"}), 400
    if not isinstance(stock_quantity, int) or stock_quantity < 0:
        return jsonify({"error": "Stock quantity is required and must be a non-negative integer"}), 400
    if description is not None and not isinstance(description, str):
        return jsonify({"error": "Description must be a string or null"}), 400

    product_id = str(uuid.uuid4())

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
            (product_id, name.strip(), description, price, stock_quantity)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500

    new_product = {
        "id": product_id,
        "name": name.strip(),
        "description": description,
        "price": price,
        "stock_quantity": stock_quantity
    }
    return jsonify(new_product), 201

@app.route('/products', methods=['GET'])
def get_all_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    return jsonify([row_to_dict(product) for product in products]), 200

@app.route('/products/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(row_to_dict(product)), 200

@app.route('/products/<string:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    if product is None:
        return jsonify({"error": "Product not found"}), 404

    # Apply partial updates and validate
    updates = {}
    if 'name' in data:
        if not isinstance(data['name'], str) or data['name'].strip() == "":
            return jsonify({"error": "Product name must be a non-empty string"}), 400
        updates['name'] = data['name'].strip()
    if 'description' in data:
        if data['description'] is not None and not isinstance(data['description'], str):
            return jsonify({"error": "Description must be a string or null"}), 400
        updates['description'] = data['description']
    if 'price' in data:
        if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
            return jsonify({"error": "Price must be a positive number"}), 400
        updates['price'] = data['price']
    if 'stock_quantity' in data:
        if not isinstance(data['stock_quantity'], int) or data['stock_quantity'] < 0:
            return jsonify({"error": "Stock quantity must be a non-negative integer"}), 400
        updates['stock_quantity'] = data['stock_quantity']

    if not updates:
        return jsonify({"error": "No valid fields provided for update"}), 400

    # Construct the SET clause for the SQL query
    set_clauses = []
    values = []
    for key, value in updates.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)

    values.append(product_id) # Add product_id for the WHERE clause

    try:
        conn.execute(
            f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?",
            tuple(values)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": f"Database error: {e}"}), 500

    # Fetch the updated product to return
    updated_product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return jsonify(row_to_dict(updated_product)), 200


@app.route('/products/<string:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    rows_affected = cursor.rowcount
    conn.commit()

    if rows_affected == 0:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({}), 204 # 204 No Content for successful deletion

if __name__ == '__main__':
    app.run(debug=True)