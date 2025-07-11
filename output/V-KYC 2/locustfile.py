from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    """
    Locust user class to simulate traffic to the FastAPI application.
    """
    wait_time = between(1, 5)  # Users wait between 1 and 5 seconds between tasks
    host = "http://localhost:8000" # Default host, can be overridden with -H

    @task(3) # This task will be executed 3 times more often than others
    def get_root(self):
        """Simulate accessing the root endpoint."""
        self.client.get("/", name="/")

    @task(2)
    def get_item_with_query(self):
        """Simulate accessing an item with a query parameter."""
        item_id = self.environment.parsed_options.item_id if self.environment.parsed_options.item_id else 1
        self.client.get(f"/items/{item_id}?q=test_query", name="/items/[id]?q")

    @task(1)
    def get_item_without_query(self):
        """Simulate accessing an item without a query parameter."""
        item_id = self.environment.parsed_options.item_id if self.environment.parsed_options.item_id else 2
        self.client.get(f"/items/{item_id}", name="/items/[id]")

    @task(1)
    def get_error(self):
        """Simulate accessing the error endpoint (expecting 500)."""
        self.client.get("/error", name="/error", allow_redirects=False)

    @task
    def get_health(self):
        """Simulate accessing the health check endpoint."""
        self.client.get("/health", name="/health")

    def on_start(self):
        """Called when a Locust user starts."""
        print(f"Starting new user: {self.environment.parsed_options.host}")

# To run Locust:
# 1. Ensure your FastAPI app is running (e.g., via `docker-compose up`)
# 2. Run Locust from your terminal:
#    locust -f locustfile.py
# 3. Open your browser to http://localhost:8089 (Locust UI)
# 4. Enter the host (e.g., http://localhost:8000) and number of users/spawn rate.
#
# For headless execution (e.g., in CI/CD):
# locust -f locustfile.py --host http://localhost:8000 --users 10 --spawn-rate 2 --run-time 30s --headless