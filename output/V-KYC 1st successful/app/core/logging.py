import logging
import sys
from app.config import settings

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL.upper())

    # Prevent adding multiple handlers if already configured
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (optional, uncomment for file logging)
        # file_handler = logging.FileHandler("app.log")
        # file_handler.setFormatter(formatter)
        # logger.addHandler(file_handler)

    return logger

# Initialize root logger for general application messages
get_logger("uvicorn") # Ensure uvicorn logs are captured
get_logger("sqlalchemy") # Ensure sqlalchemy logs are captured
get_logger("app") # Main application logs