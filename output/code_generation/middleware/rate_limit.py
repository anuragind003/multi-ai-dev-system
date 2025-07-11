from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
import asyncio

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Simple in-memory storage for rate limiting.
# In a production environment, especially with multiple instances,
# this should be replaced with a distributed store like Redis.
_request_counts = defaultdict(lambda: {"count": 0, "timestamp": 0.0})
_lock = asyncio.Lock() # To prevent race conditions on _request_counts

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Custom middleware for rate limiting API requests.
    Uses an in-memory counter, suitable for single-instance deployments.
    For multi-instance, a distributed cache (e.g., Redis) is required.
    """
    def __init__(
        self,
        app: FastAPI,
        requests_per_minute: int = settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        key_prefix: str = settings.RATE_LIMIT_KEY_PREFIX,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.key_prefix = key_prefix
        logger.info(f"RateLimitMiddleware initialized: {requests_per_minute} requests/minute.")

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Use client IP as the key for rate limiting
        # In production, consider X-Forwarded-For header if behind a proxy/load balancer
        client_ip = request.client.host if request.client else "unknown"
        rate_limit_key = f"{self.key_prefix}:{client_ip}"

        async with _lock:
            current_time = time.time()
            
            # Reset count if the minute has passed
            if current_time - _request_counts[rate_limit_key]["timestamp"] >= 60:
                _request_counts[rate_limit_key]["count"] = 0
                _request_counts[rate_limit_key]["timestamp"] = current_time

            _request_counts[rate_limit_key]["count"] += 1

            if _request_counts[rate_limit_key]["count"] > self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded. Please try again later."},
                    headers={"Retry-After": "60"} # Suggest client to retry after 60 seconds
                )
        
        response = await call_next(request)
        return response

def add_rate_limit_middleware(app: FastAPI):
    """
    Adds the custom RateLimitMiddleware to the FastAPI application.
    """
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            key_prefix=settings.RATE_LIMIT_KEY_PREFIX
        )
        logger.info("Rate Limiting middleware added.")
    else:
        logger.info("Rate Limiting is disabled by configuration.")

if __name__ == "__main__":
    # Example usage and testing
    from fastapi.testclient import TestClient

    test_app = FastAPI()
    add_rate_limit_middleware(test_app)

    @test_app.get("/test-rate-limit")
    def test_endpoint():
        return {"message": "You accessed the endpoint!"}

    client = TestClient(test_app)

    print(f"Testing rate limit: {settings.RATE_LIMIT_REQUESTS_PER_MINUTE} requests/minute")
    for i in range(settings.RATE_LIMIT_REQUESTS_PER_MINUTE + 5):
        response = client.get("/test-rate-limit")
        print(f"Request {i+1}: Status {response.status_code}")
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            print(f"Rate limit hit at request {i+1}!")
            break
    
    # Wait for a minute to reset the limit
    print("Waiting 65 seconds for rate limit reset...")
    time.sleep(65)
    response = client.get("/test-rate-limit")
    print(f"After reset, Request 1: Status {response.status_code}")
    assert response.status_code == status.HTTP_200_OK