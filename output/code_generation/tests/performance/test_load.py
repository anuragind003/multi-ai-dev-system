from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    """
    Locust user class for testing the FastAPI application.
    """
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    host = "http://localhost:8000" # Default host, overridden by LOCUST_HOST env var or -H flag

    @task(3) # This task will be executed 3 times more often than others
    def get_root(self):
        """
        Simulates a user accessing the root endpoint.
        """
        self.client.get("/", name="Get Root")

    @task(2)
    def get_health(self):
        """
        Simulates a user accessing the health check endpoint.
        """
        self.client.get("/health", name="Get Health Check")

    @task(1)
    def get_item(self):
        """
        Simulates a user accessing an item by ID.
        """
        item_id = self.environment.parsed_options.num_users # Use number of users as item_id for variety
        if item_id is None:
            item_id = 1 # Default if not running with --num-users
        self.client.get(f"/items/{item_id}", name="/items/[id]")

    @task(1)
    def get_non_existent_item(self):
        """
        Simulates a user accessing a non-existent item (should return 404).
        """
        self.client.get("/items/404", name="/items/404 (Not Found)")

    # You can add more tasks to simulate different user behaviors
    # @task
    # def post_data(self):
    #     self.client.post("/data", json={"key": "value"}, name="Post Data")