from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    """
    Locust user class to simulate traffic to the FastAPI application.
    """
    wait_time = between(1, 2.5)  # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # This task has a weight of 3, meaning it's 3 times more likely to be picked
    def get_root(self):
        """
        Simulates a user accessing the root endpoint.
        """
        self.client.get("/", name="/")

    @task(2) # This task has a weight of 2
    def get_health(self):
        """
        Simulates a health check request.
        """
        self.client.get("/health", name="/health")

    @task(1) # This task has a weight of 1
    def get_item(self):
        """
        Simulates fetching an item by ID.
        """
        item_id = self.environment.parsed_options.item_id if self.environment.parsed_options.item_id else 1
        self.client.get(f"/items/{item_id}", name="/items/[id]")

    @task
    def get_non_existent_item(self):
        """
        Simulates fetching a non-existent item to test error handling.
        """
        self.client.get("/items/0", name="/items/0", catch_response=True)

    def on_start(self):
        """
        Called when a Locust user starts.
        """
        print(f"Starting new user: {self.environment.host}")

# To run:
# 1. Ensure your FastAPI app is running (e.g., via `docker-compose up`)
# 2. Install locust: `pip install locust` or `poetry add locust`
# 3. Run locust: `locust -f app/tests/locustfile.py --host http://localhost:8000`
#    (Replace http://localhost:8000 with your deployed ALB DNS name for actual perf tests)
# 4. Open http://localhost:8089 in your browser to access the Locust UI.
# For headless run (e.g., in CI/CD):
# locust -f app/tests/locustfile.py --host http://your-alb-dns.com --users 50 --spawn-rate 5 --run-time 60s --headless --csv=locust_report --html=locust_report.html