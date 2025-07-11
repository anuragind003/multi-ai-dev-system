import logging
import sys
from config import settings

def setup_logging():
    """
    Configures the application's logging system.
    Logs to console and optionally to a file.
    """
    log_level = settings.LOG_LEVEL.upper()
    
    # Basic configuration for the root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout) # Log to console
        ]
    )

    # Optionally add a file handler for production environments
    # if settings.ENVIRONMENT == "production":
    #     file_handler = logging.handlers.RotatingFileHandler(
    #         "app.log",
    #         maxBytes=10485760, # 10 MB
    #         backupCount=5
    #     )
    #     file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    #     logging.getLogger().addHandler(file_handler)

    # Set specific log levels for noisy libraries if needed
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING) # Avoid verbose SQL logs
    logging.getLogger("slowapi").setLevel(logging.INFO)

    # Get a logger for the application
    app_logger = logging.getLogger(__name__.split('.')[0]) # Get the root app logger
    app_logger.info(f"Logging configured with level: {log_level}")