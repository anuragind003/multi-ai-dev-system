from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # This task will be executed 3 times more often than others
    def get_health(self):
        self.client.get("/health", name="/health [Health Check]")

    @task(5)
    def get_items(self):
        self.client.get("/items/", name="/items/ [Get All Items]")

    @task(1)
    def create_item(self):
        item_data = {
            "name": f"Load Test Item {self.environment.runner.stats.total.num_requests}",
            "description": "Created by Locust load test",
            "price": 100,
            "is_available": True
        }
        self.client.post("/items/", json=item_data, name="/items/ [Create Item]")

    @task(2)
    def get_single_item(self):
        # Assuming there's at least one item created by the create_item task or pre-existing
        # In a real scenario, you might fetch an ID from a previous request or a known list
        item_id = 1 # Placeholder, ideally fetch a dynamic ID
        self.client.get(f"/items/{item_id}", name="/items/{item_id} [Get Single Item]")

    @task
    def get_protected(self):
        self.client.get("/protected", name="/protected [Protected Endpoint]")