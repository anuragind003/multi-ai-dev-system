import logging
import sys
from config import get_settings

settings = get_settings()

def setup_logging():
    """
    Configures the application's logging system.
    Logs to console with a specific format.
    """
    log_level = settings.LOG_LEVEL.upper()
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Suppress verbose logging from libraries if not in debug mode
    if not settings.DEBUG_MODE:
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
        logging.getLogger("aioredis").setLevel(logging.WARNING)
        logging.getLogger("fastapi_limiter").setLevel(logging.WARNING)

    logging.info(f"Logging configured with level: {log_level}")

# Initialize logging when this module is imported
setup_logging()
logger = logging.getLogger("vkyc_api")