import requests
import time
import os

# Configuration
APP_HOST = os.getenv("APP_HOST", "http://localhost:8000")
NUM_REQUESTS = 100
CONCURRENT_USERS = 5 # Simulate concurrency by running in a loop
TEST_ENDPOINTS = ["/", "/health", "/items/1", "/items/100"] # Add more as needed

def run_performance_test():
    print(f"Starting performance test against {APP_HOST}...")
    total_requests = 0
    total_latency = 0
    successful_requests = 0
    failed_requests = 0
    start_time = time.time()

    for i in range(NUM_REQUESTS):
        for endpoint in TEST_ENDPOINTS:
            url = f"{APP_HOST}{endpoint}"
            request_start_time = time.time()
            try:
                response = requests.get(url, timeout=5)
                latency = time.time() - request_start_time
                total_latency += latency
                total_requests += 1

                if response.status_code == 200:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    print(f"Request to {url} failed with status {response.status_code}")
            except requests.exceptions.RequestException as e:
                failed_requests += 1
                total_requests += 1
                print(f"Request to {url} failed: {e}")

    end_time = time.time()
    total_test_duration = end_time - start_time

    print("\n--- Performance Test Results ---")
    print(f"Total Requests: {total_requests}")
    print(f"Successful Requests: {successful_requests}")
    print(f"Failed Requests: {failed_requests}")
    print(f"Total Test Duration: {total_test_duration:.2f} seconds")
    if successful_requests > 0:
        print(f"Average Latency: {(total_latency / successful_requests):.4f} seconds")
        print(f"Requests Per Second (RPS): {(total_requests / total_test_duration):.2f}")
    else:
        print("No successful requests to calculate average latency or RPS.")

    if failed_requests > 0:
        print("WARNING: Some requests failed during the performance test.")
        exit(1) # Fail the test if there are any failures

if __name__ == "__main__":
    # Ensure the app is running before running this test
    # For CI/CD, this would run against a deployed test environment
    run_performance_test()