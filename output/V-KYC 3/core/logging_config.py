import logging
from config import settings

def setup_logging():
    """
    Configures the application's logging.
    Logs to console and a file.
    """
    # Create logger
    logger = logging.getLogger(settings.PROJECT_NAME)
    logger.setLevel(settings.LOG_LEVEL.upper())

    # Prevent adding multiple handlers if called multiple times
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File Handler (optional, for production)
        # You might want to use a more robust logging solution like logrotate or ELK stack in production
        try:
            file_handler = logging.FileHandler("app.log")
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Could not set up file logging: {e}")

    return logger