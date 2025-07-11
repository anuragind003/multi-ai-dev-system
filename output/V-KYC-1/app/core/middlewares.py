import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

async def add_request_id_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to add a unique request ID to each incoming request
    and log it for correlation.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info(f"Request ID: {request_id} - Incoming request: {request.method} {request.url}")

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    logger.info(f"Request ID: {request_id} - Outgoing response: {response.status_code}")
    return response

# Note: CORS middleware is configured directly in app/main.py using app.add_middleware
# Rate Limiting is applied globally in app/main.py using dependencies=[RateLimiter(...)]
# and can be applied per-endpoint using @router.get("/", dependencies=[Depends(RateLimiter(...))])