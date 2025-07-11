import os
import logging
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Loguru to send logs to Logstash via TCP
# This replaces the default logging configuration for this example.
# In a real-world scenario, you might use a dedicated Logstash client library
# or a more robust logging setup. For simplicity, we'll redirect Loguru's output.
LOGSTASH_HOST = os.getenv("LOGSTASH_HOST", "logstash")
LOGSTASH_PORT = int(os.getenv("LOGSTASH_PORT", 5000))

# Remove default Loguru handler and add a custom one for Logstash
logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""), # Loguru's default print to stdout
    level="INFO",
    format="{message}", # Loguru will format to JSON in the handler below
    serialize=True # Ensure Loguru serializes to JSON
)

# Add a handler to send logs to Logstash via TCP
# This is a simplified approach. For production, consider a dedicated Logstash client
# or a more robust logging library that handles connection issues, buffering, etc.
# For this example, we'll just log to stdout as JSON, and Logstash will pick it up
# via the Docker logging driver or a Filebeat sidecar.
# The `logstash/pipeline.conf` is set up to read from stdout via Docker's logging driver.
# So, we just need to ensure our logs are JSON.

# Reconfigure standard logging to use Loguru's handler for FastAPI's internal logs
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelname

        # Find caller from where log originated
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]


app = FastAPI(
    title="FastAPI ELK Logging Demo",
    description="A simple FastAPI application demonstrating centralized logging with ELK.",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log incoming requests and their responses."""
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Outgoing response: {response.status_code} for {request.method} {request.url.path}")
    return response

@app.get("/")
async def read_root():
    """
    Root endpoint that returns a welcome message.
    Logs an info message.
    """
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to FastAPI ELK Logging Demo!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    """
    Endpoint to retrieve an item by ID.
    Logs a debug message if no query parameter is provided, otherwise info.
    """
    if q:
        logger.info(f"Item {item_id} requested with query: {q}")
    else:
        logger.debug(f"Item {item_id} requested without query parameter.")
    return {"item_id": item_id, "q": q}

@app.get("/error")
async def trigger_error():
    """
    Endpoint to simulate an error.
    Logs an error message.
    """
    try:
        1 / 0
    except ZeroDivisionError as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"message": "An internal server error occurred."})

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    logger.info("Health check endpoint accessed.")
    return {"status": "ok"}