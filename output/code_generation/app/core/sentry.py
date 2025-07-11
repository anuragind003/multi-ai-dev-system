import sentry_sdk
from sentry_sdk.integrations.fastapi import FastAPIIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import settings
from app.utils.logger import logger

def init_sentry():
    """
    Initializes Sentry SDK for error reporting.
    """
    if settings.SENTRY_DSN:
        logger.info(f"Initializing Sentry for environment: {settings.SENTRY_ENVIRONMENT}")
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN.get_secret_value() if isinstance(settings.SENTRY_DSN, sentry_sdk.Dsn) else str(settings.SENTRY_DSN),
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=1.0,  # Adjust as needed for performance monitoring
            profiles_sample_rate=1.0, # Adjust as needed for performance profiling
            integrations=[
                FastAPIIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=settings.LOG_LEVEL, # Capture logs at this level and above
                    event_level=settings.LOG_LEVEL # Send events to Sentry at this level and above
                ),
            ],
            # Set to True to see events in the console
            debug=settings.DEBUG_MODE,
        )
        logger.info("Sentry initialized successfully.")
    else:
        logger.warning("SENTRY_DSN is not set. Sentry error reporting is disabled.")

def capture_exception_to_sentry(exc: Exception, extra: dict = None):
    """
    Manually captures an exception to Sentry.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.capture_exception(exc, extras=extra)
        logger.debug(f"Exception captured by Sentry: {type(exc).__name__}")
    else:
        logger.warning("SENTRY_DSN is not set. Cannot capture exception to Sentry.")