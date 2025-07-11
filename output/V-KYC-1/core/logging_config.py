import logging
import sys
from config import settings

def configure_logging():
    """
    Configures the application's logging system.
    Sets up console and file handlers with appropriate formatters.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Clear existing handlers to prevent duplicate logs in case of reload
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Formatter for console output
    console_formatter = logging.Formatter(
        "%(levelname)s:     %(asctime)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional, useful for production)
    if not settings.DEBUG_MODE: # Only write to file in non-debug mode
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler("app.log")
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Configure uvicorn loggers to use our root logger configuration
    # This prevents uvicorn from adding its own handlers and duplicating logs
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = [] # Clear uvicorn's default handlers
    uvicorn_access_logger.propagate = True # Let logs propagate to root_logger

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers = [] # Clear uvicorn's default handlers
    uvicorn_error_logger.propagate = True # Let logs propagate to root_logger

    # Set specific log levels for noisy libraries if needed
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING) # For requests made by FastAPI's test client

    root_logger.info(f"Logging configured at level: {settings.LOG_LEVEL}")