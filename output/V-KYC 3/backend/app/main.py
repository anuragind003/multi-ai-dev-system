import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# --- Application Lifecycle Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup events
    print("Application startup: Initializing resources...")
    # Example: Connect to database
    # app.state.db_connection = await connect_to_db()
    yield
    # Shutdown events
    print("Application shutdown: Releasing resources...")
    # Example: Close database connection
    # await app.state.db_connection.close()

app = FastAPI(
    title="FastAPI Monolithic App",
    description="A production-ready FastAPI application with comprehensive operational setup.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# --- Middleware ---

# CORS Middleware
# Adjust origins based on your frontend deployment
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proxy Headers Middleware (for Nginx/Load Balancer)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # HSTS (Strict-Transport-Security) should be handled by Nginx/Load Balancer
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response

# --- Routes ---

@app.get("/", summary="Root endpoint", response_description="Welcome message")
async def read_root():
    """
    Returns a simple welcome message.
    """
    return {"message": "Welcome to the FastAPI Monolithic App!"}

@app.get("/health", summary="Health check endpoint", response_description="Health status")
async def health_check():
    """
    Checks the health of the application.
    Returns 200 OK if the application is running.
    """
    # In a real application, you might check database connection,
    # external services, etc.
    # try:
    #     await app.state.db_connection.execute("SELECT 1")
    #     db_status = "ok"
    # except Exception:
    #     db_status = "error"
    #     return JSONResponse(
    #         status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    #         content={"status": "unhealthy", "database": db_status}
    #     )
    return {"status": "healthy"}

@app.get("/items/{item_id}", summary="Get an item by ID", response_description="The requested item")
async def read_item(item_id: int):
    """
    Retrieves a single item by its ID.
    """
    if item_id == 42:
        return {"item_id": item_id, "name": "The Answer"}
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": "Item not found"}
    )

# --- Error Handling (Example) ---
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": "Not Found - The requested URL does not exist."}
    )

# You can add more routes, models, and business logic here.