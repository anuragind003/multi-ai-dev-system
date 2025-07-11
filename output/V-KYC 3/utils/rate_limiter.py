import logging
import time
from collections import defaultdict
from typing import Dict, Tuple, Callable, Any
from functools import wraps

from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# In-memory storage for rate limiting.
# In a production environment with multiple instances, this should be replaced
# with a distributed cache like Redis.
# Structure: { "ip_address": [(timestamp1, count1), (timestamp2, count2), ...] }
# Or simpler: { "ip_address": {"last_reset_time": float, "current_count": int} }
rate_limit_storage: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"last_reset_time": 0.0, "current_count": 0})

def rate_limit(max_requests: int, window_seconds: int):
    """
    A decorator for FastAPI endpoints to apply simple in-memory rate limiting
    based on client IP address.

    Args:
        max_requests (int): The maximum number of requests allowed within the window.
        window_seconds (int): The time window in seconds.
    """
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request")
            if not request:
                # If no request object, cannot apply rate limit
                logger.warning(f"Rate limit decorator applied to a function without 'request' argument: {func.__name__}")
                return await func(*args, **kwargs)

            client_ip = request.client.host if request.client else "unknown"
            current_time = time.time()

            user_data = rate_limit_storage[client_ip]
            last_reset_time = user_data["last_reset_time"]
            current_count = user_data["current_count"]

            # Check if the window has passed
            if current_time - last_reset_time > window_seconds:
                user_data["last_reset_time"] = current_time
                user_data["current_count"] = 1
                logger.debug(f"Rate limit reset for {client_ip}. New count: 1")
            else:
                user_data["current_count"] += 1
                current_count = user_data["current_count"]
                logger.debug(f"Rate limit for {client_ip}: count {current_count}/{max_requests}")

            if current_count > max_requests:
                retry_after = int(window_seconds - (current_time - last_reset_time))
                logger.warning(f"Rate limit exceeded for IP: {client_ip}. Remaining: {retry_after}s")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Please try again after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

logger.info("Rate limiting utility loaded.")

# Example usage in an endpoint:
# from utils.rate_limiter import rate_limit
#
# @router.post("/login")
# @rate_limit(max_requests=5, window_seconds=60) # 5 requests per minute
# async def login_for_access_token(...):
#     ...