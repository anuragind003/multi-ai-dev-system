from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    """
    Locust user class to simulate traffic to the FastAPI application.
    """
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # This task will be executed 3 times more often than others
    def get_root(self):
        """
        Simulate a GET request to the root endpoint.
        """
        self.client.get("/", name="/")

    @task(1)
    def get_item_even(self):
        """
        Simulate a GET request to an even item ID.
        """
        self.client.get("/items/2", name="/items/{item_id} (even)")

    @task(1)
    def get_item_odd(self):
        """
        Simulate a GET request to an odd item ID (simulated 404).
        """
        self.client.get("/items/3", name="/items/{item_id} (odd)")

    @task(0) # This task will not be executed by default, but can be manually triggered
    def get_simulate_error(self):
        """
        Simulate a GET request that triggers a 500 error.
        """
        self.client.get("/simulate_error", name="/simulate_error")

    @task(0) # This task will not be executed by default
    def get_health(self):
        """
        Simulate a GET request to the health check endpoint.
        """
        self.client.get("/health", name="/health")

    # You can add more tasks to simulate different user behaviors
    # For example, POST requests, requests with query parameters, etc.