from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    """
    Locust user class to simulate traffic to the FastAPI application.
    """
    wait_time = between(1, 2.5)  # Users wait between 1 and 2.5 seconds between tasks

    @task(10) # This task has a weight of 10 (more likely to be chosen)
    def get_root(self):
        """
        Simulates a GET request to the root endpoint.
        """
        self.client.get("/", name="/") # name is used for grouping statistics

    @task(5) # This task has a weight of 5
    def get_health(self):
        """
        Simulates a GET request to the health endpoint.
        """
        self.client.get("/health", name="/health")

    @task(1) # This task has a weight of 1 (less likely)
    def get_info(self):
        """
        Simulates a GET request to the info endpoint.
        """
        self.client.get("/info", name="/info")

    # @task(1) # Uncomment to test error rate and Sentry integration under load
    # def trigger_error(self):
    #     """
    #     Simulates a GET request to the error endpoint.
    #     This will result in a 500 error and should be captured by Sentry.
    #     """
    #     self.client.get("/error", name="/error", catch_response=True)
    #     # You might want to assert the response or log it for analysis
    #     # with self.client.get("/error", name="/error", catch_response=True) as response:
    #     #     if response.status_code == 500:
    #     #         response.success() # Mark as success if 500 is expected for error testing
    #     #     else:
    #     #         response.failure("Unexpected status code")