from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    wait_time = between(1, 2.5)  # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # Higher weight means this task is picked more often
    def get_root(self):
        self.client.get("/", name="/")

    @task(2)
    def get_health(self):
        self.client.get("/health", name="/health")

    @task(5)
    def get_item(self):
        item_id = self.environment.parsed_options.num_items or 1000 # Use a configurable number of items
        self.client.get(f"/items/{self.random.randint(1, item_id)}", name="/items/[id]")

    @task(1)
    def create_item(self):
        self.client.post("/items/", json={"name": "Locust Item", "description": "Created by performance test"}, name="/items/ [POST]")

    @task(1)
    def get_metrics(self):
        self.client.get("/metrics", name="/metrics")

    def on_start(self):
        """ on_start is called once when a Locust user starts """
        print(f"Starting new user with host: {self.host}")

# To run with a custom number of items for get_item:
# locust -f tests/performance/locustfile.py --host http://localhost:8000 --num-items 5000
# Add custom arguments for the Locust run
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.runners import LocalRunner
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Locust performance test for FastAPI app.")
    parser.add_argument("--num-items", type=int, default=1000, help="Number of items to simulate for /items/{id} endpoint.")
    args, _ = parser.parse_known_args()

    env = Environment(user_classes=[FastAPIUser])
    env.parsed_options = args # Pass custom arguments to the environment
    env.create_local_runner()
    env.create_web_ui("127.0.0.1", 8089)

    # Start a greenlet that periodically outputs the current stats
    env.spawn_greenlet(stats_printer(env.stats))
    # Start a greenlet that periodically saves the stats to a CSV file
    env.spawn_greenlet(stats_history, env.runner)

    # Start the test
    env.runner.start(user_count=10, spawn_rate=5)
    env.runner.greenlet.join() # Wait for the test to finish
    env.web_ui.stop()