import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import uvicorn

# Optional: For Prometheus metrics if you want to expose them directly from FastAPI
# from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="FastAPI Backend Service",
    description="A robust backend service for the React frontend.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"), # For development
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8080",
    # Add production frontend URL here
    # "https://your-production-frontend.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: Instrument FastAPI with Prometheus metrics
# @app.on_event("startup")
# async def startup_event():
#     Instrumentator().instrument(app).expose(app)

class HealthCheckResponse(BaseModel):
    status: str
    message: str
    service: str = "FastAPI Backend"

@app.get("/api/health", response_model=HealthCheckResponse, summary="Health Check Endpoint")
async def health_check():
    """
    Checks the health of the backend service.
    """
    return HealthCheckResponse(status="ok", message="Service is healthy")

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/api/items/", status_code=status.HTTP_201_CREATED, summary="Create a new item")
async def create_item(item: Item):
    """
    Creates a new item in the system.
    """
    return {"message": "Item created successfully", "item": item.dict()}

@app.get("/api/items/{item_id}", summary="Retrieve an item by ID")
async def read_item(item_id: int):
    """
    Retrieves a specific item by its ID.
    """
    if item_id not in [1, 2, 3]: # Dummy data
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, "name": f"Item {item_id}", "price": item_id * 10.0}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)