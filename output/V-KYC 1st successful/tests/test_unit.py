import pytest
from app.main import health_check

def test_health_check_status():
    """
    Test the health_check endpoint returns a healthy status.
    """
    response = health_check()
    assert response == {"status": "healthy", "message": "Service is up and running!"}

def test_example_unit_function():
    """
    Example of a simple unit test for a hypothetical function.
    """
    def add_numbers(a, b):
        return a + b

    assert add_numbers(2, 3) == 5
    assert add_numbers(-1, 1) == 0
    assert add_numbers(0, 0) == 0