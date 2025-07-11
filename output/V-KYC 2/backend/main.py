import os
import time
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, Counter, Histogram, Gauge
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI Backend API",
    description="A robust backend API built with FastAPI.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",  # React development server
    os.getenv("FRONTEND_URL", "http://localhost") # Production frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status_code']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint']
)
IN_PROGRESS_REQUESTS = Gauge(
    'http_requests_in_progress', 'Number of in-progress HTTP requests', ['method', 'endpoint']
)

# Middleware to collect Prometheus metrics
@app.middleware("http")
async def add_prometheus_metrics(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()

    response = await call_next(request)

    response_time = time.time() - start_time
    status_code = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(response_time)
    IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).dec()

    return response

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.get("/", response_class=HTMLResponse, summary="Root endpoint")
async def read_root():
    """
    Returns a simple HTML response for the root endpoint.
    """
    return """
    <html>
        <head>
            <title>FastAPI Backend</title>
        </head>
        <body>
            <h1>Welcome to the FastAPI Backend!</h1>
            <p>Visit <a href="/docs">/docs</a> for API documentation.</p>
            <p>Visit <a href="/health">/health</a> for health check.</p>
            <p>Visit <a href="/metrics">/metrics</a> for Prometheus metrics.</p>
        </body>
    </html>
    """

@app.get("/health", status_code=status.HTTP_200_OK, summary="Health Check")
async def health_check():
    """
    Performs a simple health check to ensure the API is running.
    """
    return {"status": "ok", "message": "API is healthy"}

@app.get("/items/{item_id}", summary="Get an item by ID")
async def read_item(item_id: int, q: str | None = None):
    """
    Retrieves a single item by its ID.
    - **item_id**: The ID of the item to retrieve.
    - **q**: An optional query string.
    """
    return {"item_id": item_id, "q": q, "message": "Item retrieved successfully"}

@app.post("/items/", status_code=status.HTTP_201_CREATED, summary="Create a new item")
async def create_item(item: Item):
    """
    Creates a new item with the provided details.
    - **name**: Name of the item.
    - **description**: Optional description.
    - **price**: Price of the item.
    - **tax**: Optional tax.
    """
    return {"message": "Item created successfully", "item": item.dict()}

@app.get("/metrics", summary="Prometheus Metrics Endpoint")
async def metrics():
    """
    Exposes Prometheus metrics for scraping.
    """
    return Response(content=generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)