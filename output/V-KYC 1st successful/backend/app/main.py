from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app, Counter, Histogram
import time
import os

app = FastAPI(
    title="FastAPI Backend Service",
    description="A simple FastAPI application serving as a backend for a Next.js frontend.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status_code']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint']
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    method = request.method
    endpoint = request.url.path
    status_code = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(process_time)

    return response

@app.get("/", summary="Root endpoint", response_description="Returns a welcome message")
async def read_root():
    """
    Returns a simple welcome message from the backend.
    """
    return {"message": "Hello from FastAPI Backend! This is a secure and scalable service."}

@app.get("/health", summary="Health check endpoint", response_description="Returns service status")
async def health_check():
    """
    Provides a health check endpoint for liveness and readiness probes.
    """
    return {"status": "ok", "timestamp": time.time()}

@app.get("/items/{item_id}", summary="Get an item by ID", response_description="Returns the item details")
async def read_item(item_id: int):
    """
    Retrieves a specific item by its ID.
    """
    if item_id == 404:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "name": f"Item {item_id}", "description": "This is a sample item."}

@app.get("/config", summary="Get backend configuration", response_description="Returns backend configuration")
async def get_config():
    """
    Returns some example configuration from environment variables.
    """
    secret_key = os.getenv("SECRET_KEY", "NOT_SET")
    return {"secret_key_status": "Set" if secret_key != "NOT_SET" else "Not Set",
            "environment": os.getenv("APP_ENV", "development")}

# Example of a custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": f"Oops! {exc.detail}"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)