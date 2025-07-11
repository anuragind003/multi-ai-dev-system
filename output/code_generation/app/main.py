import time
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from prometheus_client.core import CollectorRegistry
from prometheus_client.metrics_core import GaugeMetricFamily
import uvicorn
import os

# --- Prometheus Metrics ---
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)
APP_INFO = GaugeMetricFamily(
    'app_info',
    'Application information',
    labels=['version', 'environment']
)

# --- FastAPI Application ---
app = FastAPI(
    title="FastAPI Monitoring Service",
    description="A sample FastAPI application with integrated Prometheus monitoring.",
    version=os.getenv("APP_VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# --- Middleware for Request Metrics ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    endpoint = request.url.path
    method = request.method
    status_code = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(process_time)

    return response

# --- Health Check Endpoint ---
@app.get("/health", summary="Health Check", response_model=dict)
async def health_check():
    """
    Checks the health of the application.
    Returns a simple status indicating if the service is up.
    """
    return {"status": "healthy", "message": "Service is up and running!"}

# --- Metrics Endpoint for Prometheus ---
@app.get("/metrics", summary="Prometheus Metrics", response_class=Response)
async def metrics():
    """
    Exposes Prometheus metrics for scraping.
    """
    # Add application info metric
    app_version = os.getenv("APP_VERSION", "1.0.0")
    app_env = os.getenv("APP_ENV", "development")
    app_info_metric = APP_INFO
    app_info_metric.add_metric([app_version, app_env], 1)
    REGISTRY.register(app_info_metric) # Register temporarily for this scrape

    try:
        return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")
    finally:
        REGISTRY.unregister(app_info_metric) # Unregister to avoid re-registration errors

# --- Example Endpoint ---
@app.get("/items/{item_id}", summary="Get Item", response_model=dict)
async def read_item(item_id: int):
    """
    An example endpoint to demonstrate request handling.
    """
    if item_id == 500:
        raise HTTPException(status_code=500, detail="Simulated Internal Server Error")
    if item_id == 404:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "name": f"Item {item_id}"}

# --- Error Handling Example ---
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Increment error counter for specific HTTP exceptions
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status_code=exc.status_code).inc()
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("APP_PORT", 8000)))