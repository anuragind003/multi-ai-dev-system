import pytest

# Example of a simple function to test
def greet(name: str) -> str:
    """Returns a greeting message."""
    return f"Hello, {name}!"

def add_numbers(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

class TestUnitFunctions:
    def test_greet_function(self):
        assert greet("World") == "Hello, World!"
        assert greet("FastAPI") == "Hello, FastAPI!"

    def test_add_numbers_positive(self):
        assert add_numbers(2, 3) == 5
        assert add_numbers(10, 0) == 10

    def test_add_numbers_negative(self):
        assert add_numbers(-1, -5) == -6
        assert add_numbers(10, -3) == 7

    def test_add_numbers_zero(self):
        assert add_numbers(0, 0) == 0