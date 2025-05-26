import os
import sqlite3
import uuid
import click

from flask import Flask, request, jsonify, g, current_app
from werkzeug.exceptions import abort

def get_db():
    """
    Establishes a database connection for the current request if one doesn't exist.
    The connection is stored in Flask's `g` object.
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
    Closes the database connection at the end of the request.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    Initializes the database by executing the schema.sql script.
    """
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def create_app(test_config=None):
    """
    Flask application factory function.
    Creates and configures the Flask application.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY='dev', # Should be a strong, random key in production
        DATABASE=os.path.join(app.instance_path, 'database.db'),
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register database functions with the app
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # A simple health check route
    @app.route('/')
    def hello():
        return 'Product API is running!'

    # --- Product API Endpoints ---

    @app.route('/products', methods=['POST'])
    def create_product():
        """
        Creates a new product.
        Requires 'name', 'price', 'stock_quantity' in the request body.
        """
        data = request.get_json()

        # Input validation
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        if not data.get('name'):
            return jsonify({"error": "Product name is required"}), 400
        if not isinstance(data.get('price'), (int, float)) or data.get('price') <= 0:
            return jsonify({"error": "Price must be a positive number"}), 400
        if not isinstance(data.get('stock_quantity'), int) or data.get('stock_quantity') < 0:
            return jsonify({"error": "Stock quantity must be a non-negative integer"}), 400

        name = data['name']
        description = data.get('description', '') # Description is optional
        price = float(data['price'])
        stock_quantity = int(data['stock_quantity'])
        product_id = str(uuid.uuid4()) # Generate a unique ID (UUID)

        db = get_db()
        try:
            db.execute(
                "INSERT INTO products (id, name, description, price, stock_quantity) VALUES (?, ?, ?, ?, ?)",
                (product_id, name, description, price, stock_quantity)
            )
            db.commit()
        except sqlite3.Error as e:
            current_app.logger.error(f"Database error during product creation: {e}")
            return jsonify({"error": "Failed to create product due to a database error"}), 500
        except Exception as e:
            current_app.logger.error(f"Unexpected error during product creation: {e}")
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

        new_product = {
            "id": product_id,
            "name": name,
            "description": description,
            "price": price,
            "stock_quantity": stock_quantity
        }
        return jsonify(new_product), 201 # 201 Created

    @app.route('/products', methods=['GET'])
    def get_all_products():
        """
        Retrieves a list of all products.
        """
        db = get_db()
        products = db.execute("SELECT * FROM products").fetchall()
        return jsonify([dict(product) for product in products])

    @app.route('/products/<string:product_id>', methods=['GET'])
    def get_product_by_id(product_id):
        """
        Retrieves details for a specific product by its ID.
        """
        db = get_db()
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            return jsonify({"error": "Product not found"}), 404
        return jsonify(dict(product))

    @app.route('/products/<string:product_id>', methods=['PUT'])
    def update_product(product_id):
        """
        Updates an existing product's details by its ID. Supports partial updates.
        """
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        db = get_db()
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            return jsonify({"error": "Product not found"}), 404

        # Prepare update fields and values for partial update
        update_fields = []
        update_values = []

        if 'name' in data:
            if not data['name']:
                return jsonify({"error": "Product name cannot be empty"}), 400
            update_fields.append("name = ?")
            update_values.append(data['name'])
        if 'description' in data:
            update_fields.append("description = ?")
            update_values.append(data['description'])
        if 'price' in data:
            if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
                return jsonify({"error": "Price must be a positive number"}), 400
            update_fields.append("price = ?")
            update_values.append(float(data['price']))
        if 'stock_quantity' in data:
            if not isinstance(data['stock_quantity'], int) or data['stock_quantity'] < 0:
                return jsonify({"error": "Stock quantity must be a non-negative integer"}), 400
            update_fields.append("stock_quantity = ?")
            update_values.append(int(data['stock_quantity']))

        if not update_fields:
            return jsonify({"error": "No valid fields provided for update"}), 400

        update_query = "UPDATE products SET " + ", ".join(update_fields) + " WHERE id = ?"
        update_values.append(product_id)

        try:
            db.execute(update_query, tuple(update_values))
            db.commit()
        except sqlite3.Error as e:
            current_app.logger.error(f"Database error during product update: {e}")
            return jsonify({"error": "Failed to update product due to a database error"}), 500
        except Exception as e:
            current_app.logger.error(f"Unexpected error during product update: {e}")
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

        # Fetch the updated product to return the latest state
        updated_product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return jsonify(dict(updated_product))

    @app.route('/products/<string:product_id>', methods=['DELETE'])
    def delete_product(product_id):
        """
        Deletes a product from the system by its ID.
        """
        db = get_db()
        cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404
        return '', 204 # 204 No Content on successful deletion

    return app