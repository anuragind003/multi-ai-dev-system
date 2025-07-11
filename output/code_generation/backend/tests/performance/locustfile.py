from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    """
    Locust user class to simulate traffic to the FastAPI backend.
    """
    wait_time = between(1, 2.5)  # Users wait between 1 and 2.5 seconds between tasks

    host = "http://localhost:8000" # Default host, can be overridden by --host CLI arg

    @task(10) # This task will be executed 10 times more often than others
    def get_root(self):
        """
        Simulates a user accessing the root endpoint.
        """
        self.client.get("/", name="Get Root")

    @task(5)
    def get_health(self):
        """
        Simulates a user checking the health endpoint.
        """
        self.client.get("/health", name="Get Health")

    @task(3)
    def create_item(self):
        """
        Simulates a user creating a new item.
        """
        item_data = {
            "name": "Performance Test Item",
            "description": "Item created during performance test",
            "price": 100.0,
            "tax": 10.0
        }
        self.client.post("/items/", json=item_data, name="Create Item")

    @task(2)
    def get_item(self):
        """
        Simulates a user getting a specific item.
        """
        item_id = 1 # Using a fixed ID for simplicity, could be randomized
        self.client.get(f"/items/{item_id}", name="Get Item by ID")

    # You can add more tasks to simulate different user behaviors
    # @task(1)
    # def get_docs(self):
    #     self.client.get("/docs", name="Get Docs")