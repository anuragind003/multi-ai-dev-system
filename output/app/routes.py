import sqlite3
import uuid
from flask import request, jsonify, abort, g, current_app

# Database configuration
DATABASE = 'database.db'

def get_db():
    """Establishes a database connection or returns the existing one."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # This makes rows behave like dictionaries
    return db

def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database schema from schema.sql."""
    with current_app.app_context():
        db = get_db()
        # The schema.sql file is expected to be in the same directory as app.py or accessible via app.open_resource
        with current_app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def register_routes(app):
    """Registers all API routes with the Flask application instance."""
    app.teardown_appcontext(close_connection)

    @app.route('/products', methods=['POST'])
    def create_product():
        data = request.get_json()
        if not data:
            abort(400, description="Request body must be JSON.")

        name = data.get('name')
        price = data.get('price')
        stock_quantity = data.get('stock_quantity')
        description = data.get('description') # Optional

        # Validate required fields
        if not all([name, price is not None, stock_quantity is not None]):
            abort(400, description="Missing required fields: 'name', 'price', 'stock_quantity'.")

        # Validate data types and constraints
        if not isinstance(name, str) or not name.strip():
            abort(400, description="Name must be a non-empty string.")
        
        try:
            price = float(price)
            if price < 0:
                abort(400, description="Price cannot be negative.")
        except (ValueError, TypeError):
            abort(400, description="Price must be a valid number.")
        
        try:
            stock_quantity = int(stock_quantity)
            if stock_quantity < 0:
                abort(400, description="Stock quantity cannot be negative.")
        except (ValueError, TypeError):
            abort(400, description="Stock quantity must be a valid integer.")
        
        if description is not None and not isinstance(description, str):
            abort(400, description="Description must be a string or null.")

        product_id = str(uuid.uuid4())

        db = get_db()
        try:
            db.execute(
                "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
                (product_id, name, description, price, stock_quantity)
            )
            db.commit()
        except sqlite3.Error:
            abort(500, description="Failed to create product due to a database error.")

        new_product = {
            "id": product_id,
            "name": name,
            "description": description,
            "price": price,
            "stock_quantity": stock_quantity
        }
        return jsonify(new_product), 201

    @app.route('/products', methods=['GET'])
    def get_all_products():
        db = get_db()
        cursor = db.execute("SELECT id, name, description, price, stock_quantity FROM products")
        products = [dict(row) for row in cursor.fetchall()]
        return jsonify(products)

    @app.route('/products/<string:product_id>', methods=['GET'])
    def get_product(product_id):
        db = get_db()
        cursor = db.execute(
            "SELECT id, name, description, price, stock_quantity FROM products WHERE id = ?",
            (product_id,)
        )
        product = cursor.fetchone()
        if product is None:
            abort(404, description="Product not found.")
        return jsonify(dict(product))

    @app.route('/products/<string:product_id>', methods=['PUT'])
    def update_product(product_id):
        data = request.get_json()
        if not data:
            abort(400, description="Request body must be JSON.")

        db = get_db()
        cursor = db.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        existing_product = cursor.fetchone()

        if existing_product is None:
            abort(404, description="Product not found.")

        updates = {}
        # Process potential updates and validate
        if 'name' in data:
            if not isinstance(data['name'], str) or not data['name'].strip():
                abort(400, description="Name must be a non-empty string.")
            updates['name'] = data['name']
        
        if 'description' in data:
            if data['description'] is not None and not isinstance(data['description'], str):
                abort(400, description="Description must be a string or null.")
            updates['description'] = data['description']
        
        if 'price' in data:
            try:
                price = float(data['price'])
                if price < 0:
                    abort(400, description="Price cannot be negative.")
                updates['price'] = price
            except (ValueError, TypeError):
                abort(400, description="Price must be a valid number.")
        
        if 'stock_quantity' in data:
            try:
                stock_quantity = int(data['stock_quantity'])
                if stock_quantity < 0:
                    abort(400, description="Stock quantity cannot be negative.")
                updates['stock_quantity'] = stock_quantity
            except (ValueError, TypeError):
                abort(400, description="Stock quantity must be a valid integer.")

        if not updates:
            abort(400, description="No valid fields provided for update.")

        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)

        values.append(product_id) # Add product_id for WHERE clause

        try:
            db.execute(
                f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?",
                tuple(values)
            )
            db.commit()
        except sqlite3.Error:
            abort(500, description="An unexpected error occurred during update.")

        # Retrieve the updated product to return
        cursor = db.execute(
            "SELECT id, name, description, price, stock_quantity FROM products WHERE id = ?",
            (product_id,)
        )
        updated_product = cursor.fetchone()
        return jsonify(dict(updated_product))

    @app.route('/products/<string:product_id>', methods=['DELETE'])
    def delete_product(product_id):
        db = get_db()
        cursor = db.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()

        if product is None:
            abort(404, description="Product not found.")

        try:
            db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            db.commit()
        except sqlite3.Error:
            abort(500, description="An unexpected error occurred during deletion.")

        return jsonify({"message": "Product deleted successfully."}), 200