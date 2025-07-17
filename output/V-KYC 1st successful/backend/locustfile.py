from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    """
    Locust user class for testing the FastAPI backend.
    """
    wait_time = between(1, 2.5)  # Users wait between 1 and 2.5 seconds between tasks

    # Host of the FastAPI application.
    # In a Docker Compose setup, this would be the service name 'backend'.
    # For direct testing, it could be 'http://localhost:8000'.
    host = "http://backend:8000" # Or "http://localhost:8000" for local testing

    @task(3) # This task will be executed 3 times more often than other tasks
    def get_root(self):
        """
        Tests the root endpoint.
        """
        self.client.get("/")

    @task(5) # This task will be executed 5 times more often
    def get_items(self):
        """
        Tests fetching all items.
        """
        self.client.get("/items/", name="/items [GET]")

    @task(2) # This task will be executed 2 times more often
    def create_item(self):
        """
        Tests creating a new item.
        """
        item_data = {
            "name": f"Test Item {self.environment.stats.num_requests}",
            "description": "This is a description for a test item."
        }
        self.client.post("/items/", json=item_data, name="/items [POST]")

    @task(1) # This task will be executed once
    def get_specific_item(self):
        """
        Tests fetching a specific item by ID.
        Assumes item with ID 1 exists (e.g., created by a previous test or fixture).
        In a real scenario, you might create an item first and then fetch its ID.
        """
        item_id = 1 # Replace with a dynamic ID if possible, or ensure it exists
        self.client.get(f"/items/{item_id}", name="/items/{id} [GET]")

    # You can add more tasks for other endpoints (PUT, DELETE, etc.)
    # @task
    # def update_item(self):
    #     item_id = 1
    #     update_data = {"name": "Updated Item", "description": "Updated description."}
    #     self.client.put(f"/items/{item_id}", json=update_data, name="/items/{id} [PUT]")

    # @task
    # def delete_item(self):
    #     item_id = 2
    #     self.client.delete(f"/items/{item_id}", name="/items/{id} [DELETE]")

# To run this Locustfile:
# 1. Ensure your backend service is running (e.g., via docker-compose.dev.yml)
# 2. Install Locust: pip install locust
# 3. Run Locust from the backend directory: locust -f locustfile.py
# 4. Open your browser to http://localhost:8089 (Locust UI)
# 5. Enter the host (e.g., http://localhost:8000 or http://backend:8000 if running Locust in a separate container on the same network)
#    and number of users/spawn rate.