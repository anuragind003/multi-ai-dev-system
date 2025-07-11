import logging
from logging.handlers import RotatingFileHandler
import sys
from config import settings

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance.
    Logs to console and optionally to a rotating file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False # Prevent logs from being passed to the root logger

    # Define a common formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    # Console Handler
    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File Handler (optional, based on LOG_FILE_PATH)
    if settings.LOG_FILE_PATH and not any(isinstance(handler, RotatingFileHandler) for handler in logger.handlers):
        try:
            file_handler = RotatingFileHandler(
                settings.LOG_FILE_PATH,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to set up file logger at {settings.LOG_FILE_PATH}: {e}")

    return logger

# Initialize the root logger as well, or ensure it's not interfering
# logging.basicConfig(level=settings.LOG_LEVEL, handlers=[logging.StreamHandler(sys.stdout)])
# If you use basicConfig, it might interfere with custom handlers.
# The current approach ensures custom handlers are added only once per logger.