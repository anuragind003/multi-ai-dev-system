from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    """
    User class that does requests to the locust web server running on localhost,
    port 8000.
    """
    wait_time = between(1, 2.5) # Users will wait between 1 and 2.5 seconds between tasks

    @task(3) # This task has a weight of 3, meaning it will be executed 3 times more often than tasks with weight 1
    def get_root(self):
        """
        Simulates a user accessing the root endpoint.
        """
        self.client.get("/", name="/") # name parameter groups requests in statistics

    @task(1)
    def get_health(self):
        """
        Simulates a user accessing the health check endpoint.
        """
        self.client.get("/health", name="/health")

    @task(2)
    def get_item(self):
        """
        Simulates a user accessing an item endpoint.
        """
        item_id = self.environment.parsed_options.item_id if self.environment.parsed_options.item_id else 42
        self.client.get(f"/items/{item_id}", name="/items/[id]")

    # You can add more tasks to simulate different user behaviors
    # @task
    # def post_data(self):
    #     self.client.post("/data", json={"key": "value"})

    # on_start is called when a Locust user starts running
    def on_start(self):
        print(f"Starting user with host: {self.host}")

# To run this:
# 1. Ensure your FastAPI app is running, e.g., via `docker-compose up`
# 2. Navigate to the `backend` directory
# 3. Run: `locust -f tests/performance/test_performance.py --host http://localhost:8000`
# 4. Open your browser to http://localhost:8089 to access the Locust UI.
#    Enter the number of users and spawn rate, then start the test.