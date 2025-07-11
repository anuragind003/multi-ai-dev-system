from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # This task will be executed 3 times more often than others
    def get_root(self):
        self.client.get("/", name="Get Root")

    @task(2)
    def get_health(self):
        self.client.get("/health", name="Get Health Check")

    @task(1)
    def create_item(self):
        item_data = {
            "name": f"Test Item {self.environment.runner.stats.num_requests}",
            "description": "Description for a new item"
        }
        self.client.post("/items/", json=item_data, name="Create Item")

    @task(1)
    def get_item(self):
        # Assuming item IDs are sequential or can be predicted
        # For a real app, you might fetch existing IDs first
        item_id = self.environment.runner.stats.num_requests % 100 + 1 # Simulate fetching existing items
        self.client.get(f"/items/{item_id}", name="Get Item by ID")

    @task(0) # This task will not be executed by default, but can be enabled for specific tests
    def upload_recording(self):
        # Simulate uploading a small file
        file_content = b"This is a small test recording file."
        files = {"file": ("locust_test_recording.txt", file_content, "text/plain")}
        self.client.post("/upload-recording/", files=files, name="Upload Recording")

    def on_start(self):
        # Optional: Code to run when a user starts
        print("Starting new user session...")

    def on_stop(self):
        # Optional: Code to run when a user stops
        print("User session stopped.")

# To run:
# 1. Ensure your FastAPI app is running (e.g., via `docker-compose up`)
# 2. Run Locust: `locust -f tests/locustfile.py`
# 3. Open your browser to http://localhost:8089 (Locust web UI)
# 4. Enter the host (e.g., http://localhost:8000) and number of users/spawn rate.