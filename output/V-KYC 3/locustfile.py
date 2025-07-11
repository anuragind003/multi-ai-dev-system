from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # This task will be executed 3 times more often than others
    def get_all_items(self):
        self.client.get("/items/", name="Get All Items")

    @task(1)
    def create_and_get_item(self):
        # Create an item
        item_data = {
            "name": f"Test Item {self.environment.runner.stats.num_requests}",
            "description": "Description for load test"
        }
        create_response = self.client.post("/items/", json=item_data, name="Create Item")
        if create_response.status_code == 201:
            item_id = create_response.json()["id"]
            # Get the created item
            self.client.get(f"/items/{item_id}", name="Get Specific Item")
        else:
            create_response.failure(f"Failed to create item: {create_response.text}")

    @task(1)
    def health_check(self):
        self.client.get("/health", name="Health Check")

    # You can add more tasks for other endpoints (PUT, DELETE) if needed
    # For simplicity, focusing on GET and POST for basic load testing.