import time
from collections import defaultdict
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from config import get_settings
from utils.logger import logger

settings = get_settings()

# In-memory store for rate limiting. In production, use Redis or similar.
# { "ip_address": [(timestamp1, count1), (timestamp2, count2), ...] }
request_timestamps = defaultdict(list)
CLEANUP_INTERVAL = 60 # seconds to clean up old entries

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for basic in-memory rate limiting based on IP address.
    """
    def __init__(self, app):
        super().__init__(app)
        self.last_cleanup_time = time.time()

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean up old timestamps periodically
        if current_time - self.last_cleanup_time > CLEANUP_INTERVAL:
            self._cleanup_old_requests(current_time)
            self.last_cleanup_time = current_time

        # Remove timestamps older than the rate limit window
        self._remove_expired_timestamps(client_ip, current_time)

        # Check if rate limit is exceeded
        if len(request_timestamps[client_ip]) >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Max {settings.RATE_LIMIT_REQUESTS_PER_MINUTE} requests per minute."}
            )

        # Add current request timestamp
        request_timestamps[client_ip].append(current_time)
        logger.debug(f"Request from {client_ip}. Current requests in window: {len(request_timestamps[client_ip])}")

        response = await call_next(request)
        return response

    def _remove_expired_timestamps(self, ip: str, current_time: float):
        """Removes timestamps older than the rate limit window for a specific IP."""
        request_timestamps[ip] = [
            ts for ts in request_timestamps[ip]
            if current_time - ts < 60 # 60 seconds window
        ]

    def _cleanup_old_requests(self, current_time: float):
        """Cleans up all IP entries that have no recent requests."""
        ips_to_remove = []
        for ip, timestamps in request_timestamps.items():
            request_timestamps[ip] = [
                ts for ts in timestamps
                if current_time - ts < 60 # 60 seconds window
            ]
            if not request_timestamps[ip]:
                ips_to_remove.append(ip)

        for ip in ips_to_remove:
            del request_timestamps[ip]
        logger.debug(f"Rate limit cleanup performed. Active IPs: {len(request_timestamps)}")