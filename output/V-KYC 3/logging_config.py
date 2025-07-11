import logging
import sys
from logging.handlers import RotatingFileHandler
import json

class JsonFormatter(logging.Formatter):
    """
    A custom logging formatter that outputs logs in JSON format.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName,
            "process": record.process,
            "thread": record.thread,
            "exc_info": self.formatException(record.exc_info) if record.exc_info else None,
            "stack_info": self.formatStack(record.stack_info) if record.stack_info else None,
        }
        # Add extra attributes if present
        if hasattr(record, 'extra_data'):
            log_record.update(record.extra_data)
        return json.dumps(log_record)

def setup_logging():
    """
    Configures the application's logging system.
    Sets up console and file handlers with different formats.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Default level for all handlers

    # Prevent duplicate loggers from multiple calls
    if not root_logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(levelname)s:     %(asctime)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File Handler (for structured JSON logs)
        file_handler = RotatingFileHandler(
            "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_formatter = JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO) # File handler can have a different level
        root_logger.addHandler(file_handler)

        # Set specific log levels for libraries to reduce noise
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("fastapi_limiter").setLevel(logging.INFO)

        # Example of how to set a specific module's log level
        # logging.getLogger("your_module_name").setLevel(logging.DEBUG)

        root_logger.info("Logging configured successfully.")