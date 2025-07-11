from fastapi import FastAPI, Request, Response
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def configure_performance_monitoring(app: FastAPI):
    """
    Configures middleware for performance monitoring.
    """
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(f"Request processed in {process_time:.4f}s, Path: {request.url.path}, Method: {request.method}")
        return response

def configure_caching(app: FastAPI, cache_time: int = 60):
    """
    Configures response caching using a simple in-memory cache.
    (Consider using a dedicated caching solution like Redis for production)
    """
    cache = {}

    @app.middleware("http")
    async def cache_middleware(request: Request, call_next):
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        # Create a cache key based on the request URL
        cache_key = str(request.url)

        # Check if the response is in the cache
        if cache_key in cache:
            cached_response, cached_time = cache[cache_key]
            if time.time() - cached_time < cache_time:
                logger.info(f"Returning cached response for {cache_key}")
                return cached_response

        # If not in cache, process the request
        response: Response = await call_next(request)

        # Cache the response
        cache[cache_key] = (response, time.time())
        logger.info(f"Caching response for {cache_key}")
        return response