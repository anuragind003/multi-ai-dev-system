import pytest
import json
import uuid

# Assuming the Flask app and database initialization functions are in 'app.py'
# We need to import them to set up the test environment.
# The 'app' module should expose a function like 'create_app'
# and a function like 'init_db' that sets up the database schema.
from app import create_app, init_db


@pytest.fixture
def client():
    """
    Configures the Flask app for testing, sets up an in-memory SQLite database,
    initializes the database schema, and provides a test client.
    """
    app = create_app()
    app.config['TESTING'] = True
    # Use an in-memory SQLite database for testing
    app.config['DATABASE'] = ':memory:'

    with app.test_client() as client:
        # Push an application context to initialize the database
        with app.app_context():
            init_db()
        yield client


def test_create_product_success(client):
    """
    Tests successful creation of a new product.
    """
    product_data = {
        "name": "Test Product",
        "description": "A product for testing purposes.",
        "price": 99.99,
        "stock_quantity": 10
    }
    response = client.post("/products", json=product_data)
    data = json.loads(response.data)

    assert response.status_code == 201
    assert "id" in data
    assert data["name"] == product_data["name"]
    assert data["description"] == product_data["description"]
    assert data["price"] == product_data["price"]
    assert data["stock_quantity"] == product_data["stock_quantity"]


def test_create_product_missing_required_fields(client):
    """
    Tests creating a product with missing required fields.
    """
    # Missing 'name'
    product_data = {
        "description": "A product for testing purposes.",
        "price": 99.99,
        "stock_quantity": 10
    }
    response = client.post("/products", json=product_data)
    assert response.status_code == 400
    assert "error" in json.loads(response.data)

    # Missing 'price'
    product_data = {
        "name": "Test Product",
        "description": "A product for testing purposes.",
        "stock_quantity": 10
    }
    response = client.post("/products", json=product_data)
    assert response.status_code == 400
    assert "error" in json.loads(response.data)

    # Missing 'stock_quantity'
    product_data = {
        "name": "Test Product",
        "description": "A product for testing purposes.",
        "price": 99.99
    }
    response = client.post("/products", json=product_data)
    assert response.status_code == 400
    assert "error" in json.loads(response.data)


def test_create_product_invalid_data_types(client):
    """
    Tests creating a product with invalid data types for fields.
    """
    product_data = {
        "name": "Test Product",
        "description": "A product for testing purposes.",
        "price": "invalid_price",  # Invalid type
        "stock_quantity": 10
    }
    response = client.post("/products", json=product_data)
    assert response.status_code == 400
    assert "error" in json.loads(response.data)

    product_data = {
        "name": "Test Product",
        "description": "A product for testing purposes.",
        "price": 99.99,
        "stock_quantity": "invalid_stock"  # Invalid type
    }
    response = client.post("/products", json=product_data)
    assert response.status_code == 400
    assert "error" in json.loads(response.data)


def test_get_all_products_empty(client):
    """
    Tests retrieving all products when no products exist.
    """
    response = client.get("/products")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_all_products_with_data(client):
    """
    Tests retrieving all products when products exist.
    """
    product1_data = {
        "name": "Product A",
        "description": "Desc A",
        "price": 10.0,
        "stock_quantity": 100
    }
    product2_data = {
        "name": "Product B",
        "description": "Desc B",
        "price": 20.0,
        "stock_quantity": 200
    }
    client.post("/products", json=product1_data)
    client.post("/products", json=product2_data)

    response = client.get("/products")
    data = json.loads(response.data)

    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) == 2
    # Check if the names are present in the returned list
    assert any(p["name"] == "Product A" for p in data)
    assert any(p["name"] == "Product B" for p in data)


def test_get_product_by_id_success(client):
    """
    Tests retrieving a specific product by its ID successfully.
    """
    product_data = {
        "name": "Unique Product",
        "description": "Description for unique product.",
        "price": 50.0,
        "stock_quantity": 5
    }
    post_response = client.post("/products", json=product_data)
    created_product = json.loads(post_response.data)
    product_id = created_product["id"]

    get_response = client.get(f"/products/{product_id}")
    retrieved_product = json.loads(get_response.data)

    assert get_response.status_code == 200
    assert retrieved_product["id"] == product_id
    assert retrieved_product["name"] == product_data["name"]
    assert retrieved_product["price"] == product_data["price"]


def test_get_product_by_id_not_found(client):
    """
    Tests retrieving a product with a non-existent ID.
    """
    non_existent_id = str(uuid.uuid4())  # Generate a valid-looking but non-existent UUID
    response = client.get(f"/products/{non_existent_id}")
    assert response.status_code == 404
    assert "error" in json.loads(response.data)


def test_update_product_full_success(client):
    """
    Tests full update of an existing product.
    """
    product_data = {
        "name": "Original Product",
        "description": "Original description.",
        "price": 10.0,
        "stock_quantity": 10
    }
    post_response = client.post("/products", json=product_data)
    created_product = json.loads(post_response.data)
    product_id = created_product["id"]

    updated_data = {
        "name": "Updated Product",
        "description": "New description.",
        "price": 15.0,
        "stock_quantity": 15
    }
    put_response = client.put(f"/products/{product_id}", json=updated_data)
    updated_product = json.loads(put_response.data)

    assert put_response.status_code == 200
    assert updated_product["id"] == product_id
    assert updated_product["name"] == updated_data["name"]
    assert updated_product["description"] == updated_data["description"]
    assert updated_product["price"] == updated_data["price"]
    assert updated_product["stock_quantity"] == updated_data["stock_quantity"]

    # Verify by fetching again
    get_response = client.get(f"/products/{product_id}")
    verified_product = json.loads(get_response.data)
    assert verified_product["name"] == updated_data["name"]


def test_update_product_partial_success(client):
    """
    Tests partial update of an existing product.
    """
    product_data = {
        "name": "Original Product",
        "description": "Original description.",
        "price": 10.0,
        "stock_quantity": 10
    }
    post_response = client.post("/products", json=product_data)
    created_product = json.loads(post_response.data)
    product_id = created_product["id"]

    partial_update_data = {
        "price": 12.5,
        "stock_quantity": 8
    }
    put_response = client.put(f"/products/{product_id}", json=partial_update_data)
    updated_product = json.loads(put_response.data)

    assert put_response.status_code == 200
    assert updated_product["id"] == product_id
    assert updated_product["name"] == product_data["name"]  # Should remain unchanged
    assert updated_product["description"] == product_data["description"]  # Should remain unchanged
    assert updated_product["price"] == partial_update_data["price"]
    assert updated_product["stock_quantity"] == partial_update_data["stock_quantity"]

    # Verify by fetching again
    get_response = client.get(f"/products/{product_id}")
    verified_product = json.loads(get_response.data)
    assert verified_product["price"] == partial_update_data["price"]
    assert verified_product["stock_quantity"] == partial_update_data["stock_quantity"]
    assert verified_product["name"] == product_data["name"]


def test_update_product_not_found(client):
    """
    Tests updating a non-existent product.
    """
    non_existent_id = str(uuid.uuid4())
    update_data = {"name": "Non Existent Update"}
    response = client.put(f"/products/{non_existent_id}", json=update_data)
    assert response.status_code == 404
    assert "error" in json.loads(response.data)


def test_update_product_invalid_data(client):
    """
    Tests updating a product with invalid data types.
    """
    product_data = {
        "name": "Original Product",
        "description": "Original description.",
        "price": 10.0,
        "stock_quantity": 10
    }
    post_response = client.post("/products", json=product_data)
    created_product = json.loads(post_response.data)
    product_id = created_product["id"]

    invalid_update_data = {
        "price": "invalid_price_type"
    }
    response = client.put(f"/products/{product_id}", json=invalid_update_data)
    assert response.status_code == 400
    assert "error" in json.loads(response.data)


def test_delete_product_success(client):
    """
    Tests successful deletion of a product.
    """
    product_data = {
        "name": "Product to Delete",
        "description": "This product will be deleted.",
        "price": 1.0,
        "stock_quantity": 1
    }
    post_response = client.post("/products", json=product_data)
    created_product = json.loads(post_response.data)
    product_id = created_product["id"]

    delete_response = client.delete(f"/products/{product_id}")
    data = json.loads(delete_response.data)

    assert delete_response.status_code == 200
    assert "message" in data
    assert data["message"] == "Product deleted successfully"

    # Verify deletion by trying to retrieve the product
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404


def test_delete_product_not_found(client):
    """
    Tests deleting a non-existent product.
    """
    non_existent_id = str(uuid.uuid4())
    response = client.delete(f"/products/{non_existent_id}")
    assert response.status_code == 404
    assert "error" in json.loads(response.data)