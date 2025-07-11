from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    """
    User class that does requests to the locust web app running on localhost,
    port 8000.
    """
    wait_time = between(1, 2.5) # Users wait 1 to 2.5 seconds between tasks

    @task(3) # This task will be executed 3 times more often than others
    def health_check(self):
        """
        Simulates a user checking the health endpoint.
        """
        self.client.get("/api/v1/health")

    @task(1)
    def root_redirect(self):
        """
        Simulates a user accessing the root endpoint, which redirects.
        """
        self.client.get("/", allow_redirects=True)

    # Example of a more complex task, e.g., for a protected endpoint
    # @task(1)
    # def protected_route(self):
    #     """
    #     Simulates accessing a protected route.
    #     Requires a valid token, which would be obtained via a login task.
    #     """
    #     # In a real scenario, you'd have a login task to get a token first
    #     # self.client.post("/token", json={"username": "testuser", "password": "testpassword"})
    #     # token = self.client.response.json()["access_token"]
    #     # headers = {"Authorization": f"Bearer {token}"}
    #     # self.client.get("/protected-route", headers=headers)
    #     self.client.get("/protected-route", headers={"Authorization": "Bearer fake_token"}) # Mocked for this example