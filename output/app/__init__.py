import sqlite3
import uuid
from flask import Flask, request, jsonify, g
from werkzeug.exceptions import HTTPException

# Database configuration
DATABASE = 'database.db'

def get_db():
    """
    Establishes a database connection or returns the existing one.
    The connection is stored in Flask's `g` object, which is unique per request.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # Configure row_factory to return rows that behave like dictionaries
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """
    Closes the database connection at the end of the request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initializes the database schema.
    This function should be called once, typically via a Flask CLI command.
    """
    db = get_db()
    # Database schema from project context
    schema = """
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    );
    """
    db.executescript(schema)
    db.commit()

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)

    # Register the close_db function to be called after each request
    app.teardown_appcontext(close_db)

    # Add a command to initialize the database via Flask CLI
    # To run: flask --app app init-db
    @app.cli.command('init-db')
    def init_db_command():
        """Clear the existing data and create new tables."""
        init_db()
        print('Initialized the database.')

    # Custom error handlers for JSON responses
    @app.errorhandler(400)
    def bad_request(error):
        # For HTTPException, description is usually set. For others, use a default.
        message = getattr(error, 'description', 'The request could not be understood by the server due to malformed syntax.')
        return jsonify({"error": "Bad Request", "message": message}), 400

    @app.errorhandler(404)
    def not_found(error):
        message = getattr(error, 'description', 'The requested resource was not found on the server.')
        return jsonify({"error": "Not Found", "message": message}), 404

    # API Endpoints

    @app.route('/products', methods=['POST'])
    def create_product():
        """
        Creates a new product.
        Expects JSON with 'name', 'price', 'stock_quantity', and optional 'description'.
        """
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON", "message": "Request body must be JSON."}), 400

        name = data.get('name')
        price = data.get('price')
        stock_quantity = data.get('stock_quantity')
        description = data.get('description', '') # Default to empty string if not provided

        # Input validation
        if not isinstance(name, str) or not name.strip():
            return jsonify({"error": "Validation Error", "message": "Product 'name' is required and must be a non-empty string."}), 400
        if not isinstance(price, (int, float)) or price < 0:
            return jsonify({"error": "Validation Error", "message": "Product 'price' is required and must be a non-negative number."}), 400
        if not isinstance(stock_quantity, int) or stock_quantity < 0:
            return jsonify({"error": "Validation Error", "message": "Product 'stock_quantity' is required and must be a non-negative integer."}), 400
        if description is not None and not isinstance(description, str):
            return jsonify({"error": "Validation Error", "message": "Product 'description' must be a string or null."}), 400

        product_id = str(uuid.uuid4())
        db = get_db()
        try:
            db.execute(
                "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
                (product_id, name.strip(), description.strip(), price, stock_quantity)
            )
            db.commit()
        except sqlite3.Error as e:
            # Catch specific SQLite errors for better debugging/logging
            return jsonify({"error": "Database Error", "message": f"Failed to create product: {e}"}), 500
        except Exception as e:
            # Catch any other unexpected errors
            return jsonify({"error": "Internal Server Error", "message": f"An unexpected error occurred: {e}"}), 500

        new_product = {
            "id": product_id,
            "name": name.strip(),
            "description": description.strip(),
            "price": price,
            "stock_quantity": stock_quantity
        }
        return jsonify(new_product), 201

    @app.route('/products', methods=['GET'])
    def get_all_products():
        """
        Retrieves a list of all products.
        """
        db = get_db()
        products = db.execute("SELECT * FROM products").fetchall()
        # Convert Row objects to dictionaries for jsonify
        return jsonify([dict(product) for product in products]), 200

    @app.route('/products/<string:product_id>', methods=['GET'])
    def get_product(product_id):
        """
        Retrieves details for a specific product by its unique ID.
        """
        db = get_db()
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            return jsonify({"error": "Not Found", "message": f"Product with ID '{product_id}' not found."}), 404
        return jsonify(dict(product)), 200

    @app.route('/products/<string:product_id>', methods=['PUT'])
    def update_product(product_id):
        """
        Modifies an existing product's details by ID, supporting partial updates.
        Expects JSON with fields to update.
        """
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON", "message": "Request body must be JSON."}), 400

        db = get_db()
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            return jsonify({"error": "Not Found", "message": f"Product with ID '{product_id}' not found."}), 404

        updates = {}
        # Validate and collect updates
        if 'name' in data:
            if not isinstance(data['name'], str) or not data['name'].strip():
                return jsonify({"error": "Validation Error", "message": "Product 'name' must be a non-empty string."}), 400
            updates['name'] = data['name'].strip()
        if 'description' in data:
            # Allow description to be null or empty string
            if data['description'] is not None and not isinstance(data['description'], str):
                return jsonify({"error": "Validation Error", "message": "Product 'description' must be a string or null."}), 400
            updates['description'] = data['description'].strip() if data['description'] else ''
        if 'price' in data:
            if not isinstance(data['price'], (int, float)) or data['price'] < 0:
                return jsonify({"error": "Validation Error", "message": "Product 'price' must be a non-negative number."}), 400
            updates['price'] = data['price']
        if 'stock_quantity' in data:
            if not isinstance(data['stock_quantity'], int) or data['stock_quantity'] < 0:
                return jsonify({"error": "Validation Error", "message": "Product 'stock_quantity' must be a non-negative integer."}), 400
            updates['stock_quantity'] = data['stock_quantity']

        if not updates:
            return jsonify({"error": "No Content", "message": "No valid fields provided for update."}), 400

        # Construct the UPDATE query dynamically
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)

        values.append(product_id) # Add product_id for the WHERE clause

        try:
            db.execute(
                f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?",
                tuple(values)
            )
            db.commit()
        except sqlite3.Error as e:
            return jsonify({"error": "Database Error", "message": f"Failed to update product: {e}"}), 500
        except Exception as e:
            return jsonify({"error": "Internal Server Error", "message": f"An unexpected error occurred during update: {e}"}), 500

        # Retrieve and return the updated product details
        updated_product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return jsonify(dict(updated_product)), 200

    @app.route('/products/<string:product_id>', methods=['DELETE'])
    def delete_product(product_id):
        """
        Removes a product from the system using its ID.
        """
        db = get_db()
        cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Not Found", "message": f"Product with ID '{product_id}' not found."}), 404
        
        return jsonify({"message": "Product deleted successfully."}), 200

    return app