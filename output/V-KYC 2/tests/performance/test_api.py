from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    wait_time = between(1, 2.5) # Users wait between 1 and 2.5 seconds between tasks

    @task(3) # 3 times more likely to be picked than other tasks
    def get_root(self):
        self.client.get("/")

    @task(5) # 5 times more likely
    def get_health(self):
        self.client.get("/health")

    @task(1)
    def set_and_get_cache(self):
        # Generate a unique key for each request to avoid cache hits for different users
        key = f"perf_test_key_{self.environment.runner.stats.num_requests}"
        value = "performance_test_value"
        ttl = 60 # Cache for 60 seconds

        # Set cache
        self.client.post("/cache", json={"key": key, "value": value, "ttl": ttl}, name="/cache [POST]")

        # Get cache
        self.client.get(f"/cache/{key}", name="/cache/{key} [GET]")

    @task(2)
    def session_counter(self):
        # Simulate a user session by passing the session_id cookie
        # Locust automatically handles cookies for a given HttpUser instance
        self.client.get("/session_counter")