# tests/test_performance.py - Performance tests using Locust

from locust import HttpUser, task, between
import os

# Get target host from environment variable (set by CI/CD or locally)
TARGET_HOST = os.getenv("TARGET_HOST", "http://localhost:8000")

class FastAPIUser(HttpUser):
    """
    Locust user class for testing the FastAPI application.
    """
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks
    host = TARGET_HOST

    @task(10) # Higher weight, this task will be executed more often
    def get_root(self):
        """
        Simulates a user accessing the root endpoint.
        """
        self.client.get("/", name="/")

    @task(5) # Medium weight
    def get_health(self):
        """
        Simulates a user checking the health endpoint.
        """
        self.client.get("/health", name="/health")

    @task(3) # Lower weight
    def create_item(self):
        """
        Simulates a user creating a new item.
        """
        item_data = {
            "name": f"Perf Test Item {self.environment.stats.num_requests}",
            "description": "Item created during performance test",
            "price": 100.00,
            "tax": 5.00
        }
        self.client.post("/items/", json=item_data, name="/items/ [POST]")

    @task(1) # Lowest weight, requires an existing item ID
    def get_item(self):
        """
        Simulates a user retrieving an item by ID.
        Note: This task assumes items exist with IDs.
        For a more robust test, you might create items in an @on_start method
        and store their IDs, or use a range of known IDs.
        For simplicity, we'll try a few common IDs.
        """
        item_id = self.environment.stats.num_requests % 10 + 1 # Cycle through IDs 1-10
        self.client.get(f"/items/{item_id}", name="/items/{item_id} [GET]")

# To run locally:
# 1. Ensure your FastAPI app is running (e.g., `docker-compose up`)
# 2. Set the TARGET_HOST environment variable: `export TARGET_HOST=http://localhost:8000`
# 3. Run Locust: `locust -f tests/test_performance.py`
# 4. Open your browser to http://localhost:8089 (Locust UI)
#
# To run in CI/CD (headless):
# locust -f tests/test_performance.py --headless -u 10 -r 5 --run-time 30s --html locust_report.html
# -u 10: 10 users
# -r 5: 5 users/second spawn rate
# --run-time 30s: Run for 30 seconds
# --html locust_report.html: Generate an HTML report