from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    """
    User class that does requests to the locust web app running on localhost,
    port 8000.
    """
    wait_time = between(1, 2.5) # Users will wait between 1 and 2.5 seconds between tasks

    # Host for the API. This can be overridden via command line --host
    # or by setting the LOCUST_HOST environment variable.
    host = "http://localhost:8000"

    # Define common headers, e.g., for authentication
    common_headers = {
        "Authorization": "Bearer supersecrettoken",
        "Content-Type": "application/json"
    }

    @task(3) # This task will be executed 3 times more often than others
    def get_root(self):
        """
        Simulates a user accessing the root endpoint.
        """
        self.client.get("/", name="/") # name is used for statistics grouping

    @task(2)
    def get_health(self):
        """
        Simulates a user checking the health endpoint.
        """
        self.client.get("/health", name="/health")

    @task(1)
    def get_item(self):
        """
        Simulates a user accessing an authenticated item endpoint.
        """
        item_id = self.environment.stats.num_requests % 100 + 1 # Cycle through item IDs
        self.client.get(f"/items/{item_id}", headers=self.common_headers, name="/items/[id]")

    @task(1)
    def post_data(self):
        """
        Simulates a user posting data to an endpoint.
        """
        data = {"key": f"value_{self.environment.stats.num_requests}", "timestamp": self.environment.stats.num_requests}
        self.client.post("/data", json=data, name="/data")

    @task(0) # This task will not be executed by default, but can be called explicitly
    def get_metrics(self):
        """
        Simulates accessing the metrics endpoint (less frequent).
        """
        self.client.get("/metrics", name="/metrics")

    def on_start(self):
        """
        Called when a Locust user starts. Can be used for login, etc.
        """
        print(f"Starting new user on host: {self.host}")
        # Example: If login was required for all tasks
        # self.client.post("/login", json={"username": "test", "password": "password"})

    def on_stop(self):
        """
        Called when a Locust user stops. Can be used for logout, etc.
        """
        print("User stopped.")

# To run this:
# 1. Ensure your FastAPI app is running (e.g., via `docker-compose up backend`).
# 2. Install Locust: `pip install locust`
# 3. Run Locust: `locust -f backend/tests/performance/locustfile.py`
# 4. Open your browser to http://localhost:8089 (Locust UI)