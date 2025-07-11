import pytest
from fastapi.testclient import TestClient
from app.main import app
import logging

# Suppress Loguru's output during tests
logging.getLogger("loguru").propagate = False

client = TestClient(app)

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI ELK Logging Demo!"}

def test_read_item_with_query():
    """Test the item endpoint with a query parameter."""
    response = client.get("/items/123?q=test_query")
    assert response.status_code == 200
    assert response.json() == {"item_id": 123, "q": "test_query"}

def test_read_item_without_query():
    """Test the item endpoint without a query parameter."""
    response = client.get("/items/456")
    assert response.status_code == 200
    assert response.json() == {"item_id": 456, "q": None}

def test_trigger_error():
    """Test the error endpoint to ensure it returns 500."""
    response = client.get("/error")
    assert response.status_code == 500
    assert response.json() == {"message": "An internal server error occurred."}

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# Example of an integration test (requires ELK to be running, typically in a separate test stage)
# This test would be more complex, involving checking Elasticsearch for logs.
# For simplicity, this is commented out as it requires a running ELK stack.
# def test_log_to_elk(caplog):
#     """
#     Integration test: Verify logs are sent to ELK.
#     This would require a running ELK stack and a way to query Elasticsearch.
#     """
#     # Simulate a request that generates a log
#     response = client.get("/")
#     assert response.status_code == 200
#
#     # In a real integration test, you would query Elasticsearch
#     # to confirm the log entry exists.
#     # Example (pseudo-code):
#     # es_client = Elasticsearch(hosts=["localhost:9200"])
#     # time.sleep(2) # Give Logstash time to process
#     # search_result = es_client.search(index="fastapi-logs-*", body={"query": {"match": {"message": "Root endpoint accessed."}}})
#     # assert search_result['hits']['total']['value'] > 0
#
#     # For unit test, we can check if Loguru captured it (less useful for ELK integration)
#     assert "Root endpoint accessed." in caplog.text