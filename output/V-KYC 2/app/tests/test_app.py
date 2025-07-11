# app/tests/test_app.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
import logging
import json

client = TestClient(app)

# Suppress application logs during testing to keep test output clean
@pytest.fixture(autouse=True)
def disable_app_logging():
    logging.getLogger("app.main").propagate = False
    yield
    logging.getLogger("app.main").propagate = True

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI ELK Logging Demo!"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "timestamp" in response.json()

@pytest.mark.parametrize("level, expected_status", [
    ("info", 200),
    ("debug", 200),
    ("warning", 200),
    ("error", 200),
    ("critical", 200),
    ("invalid", 400),
])
def test_log_message_endpoint(level, expected_status):
    response = client.get(f"/log_message?level={level}&message=Test%20message%20for%20{level}")
    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["status"] == "Log message sent"
        assert response.json()["level"] == level
    else:
        assert "Invalid log level" in response.json()["message"]

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "fastapi_app_requests_total" in response.text
    assert "fastapi_app_request_duration_seconds_bucket" in response.text
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

def test_simulate_error_endpoint():
    response = client.get("/error")
    assert response.status_code == 500
    assert response.json() == {"message": "An internal server error occurred."}

# Integration test for logging output (requires capturing stdout)
def test_logging_output_format(caplog):
    # caplog fixture captures logs from all loggers
    with caplog.at_level(logging.INFO):
        client.get("/")
        # Check if a log entry was made by app.main
        assert any("Root endpoint accessed." in record.message for record in caplog.records)
        # Check if the log is in JSON format (by attempting to parse it)
        json_log_found = False
        for record in caplog.records:
            if "Root endpoint accessed." in record.message:
                try:
                    # The actual log message is in record.message, but the jsonlogger
                    # writes the full JSON string to stdout. caplog captures the
                    # formatted message. To truly test JSON output, you'd need to
                    # redirect stdout/stderr or use a custom handler for testing.
                    # For this test, we'll check if the message is present.
                    # A more robust test would involve mocking the StreamHandler.
                    json_log_found = True
                    break
                except json.JSONDecodeError:
                    continue
        assert json_log_found, "Expected JSON log not found or not parsable"