from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task
    def get_root(self):
        self.client.get("/")

    @task
    def get_health(self):
        self.client.get("/health")

    @task(3) # This task will be executed 3 times more often than others
    def get_item(self):
        # Simulate fetching different items
        item_id = self.environment.parsed_options.item_id if self.environment.parsed_options.item_id else 1
        self.client.get(f"/items/{item_id}")

    @task(1) # Less frequent task
    def create_item(self):
        self.client.post("/items/", json={"name": "Test Item", "description": "Created by Locust"})

    # You can add more tasks to simulate different user behaviors

    # To run: locust -f tests/performance/locustfile.py --host http://localhost:8000
    # For CI/CD, you might run this against a staging environment and set thresholds.
    # Example command for CI/CD with headless run and report:
    # locust -f tests/performance/locustfile.py --host http://your-staging-api.com --users 100 --spawn-rate 10 --run-time 5m --headless --html locust_report.html