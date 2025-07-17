from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # This task will be executed 3 times more often than others
    def health_check(self):
        self.client.get("/health", name="Health Check")

    @task(2)
    def read_root(self):
        self.client.get("/", name="Read Root")

    @task(1)
    def create_item(self):
        item_data = {
            "name": "Performance Test Item",
            "description": "Item created by performance test",
            "price": 100.0,
            "tax": 5.0
        }
        self.client.post("/items/", json=item_data, name="Create Item")

    @task(1)
    def read_item(self):
        item_id = self.environment.parsed_options.num_users # Use user count as ID for variety
        self.client.get(f"/items/{item_id}", name="Read Item by ID")

    @task(1)
    def get_config(self):
        self.client.get("/config", name="Get Config")

    # To run:
    # 1. Ensure your FastAPI app is running (e.g., via `docker-compose up`)
    # 2. Run `locust -f locustfile.py`
    # 3. Open your browser to http://localhost:8089 (Locust web UI)
    # 4. Enter the host (e.g., http://localhost:8000), number of users, and spawn rate.
    # 5. Click "Start swarming".

    # For headless execution (e.g., in CI/CD):
    # locust -f locustfile.py --host http://your-api-host:8000 --users 10 --spawn-rate 2 --run-time 60s --headless --csv=locust_results