from celery import Celery
from flask import Flask


# Initialize Celery without specific broker/backend yet.
# These will be configured when `init_celery` is called with the Flask app.
celery_app = Celery(__name__)


def init_celery(app: Flask) -> Celery:
    """
    Initializes the Celery app with Flask application context and configuration.
    This allows Celery tasks to access Flask's configuration and extensions.

    Args:
        app (Flask): The Flask application instance.

    Returns:
        Celery: The configured Celery application instance.
    """
    # Update Celery configuration from Flask app's config.
    # It's good practice to prefix Celery-specific configs in Flask,
    # e.g., 'CELERY_BROKER_URL'.
    celery_app.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        timezone='UTC',  # Good practice to set a timezone
        enable_utc=True,
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        broker_connection_retry_on_startup=True,  # Recommended for production
        # List of modules to import when the Celery worker starts.
        # This helps Celery discover tasks defined in these modules.
        # Assuming tasks are defined in files like ingestion.py, deduplication.py etc.
        # within the 'tasks' directory.
        imports=(
            'backend.tasks.ingestion',
            'backend.tasks.deduplication',
            'backend.tasks.offer_management',
            'backend.tasks.reporting',
            'backend.tasks.data_export',
            'backend.tasks.event_tracking',
            'backend.tasks.cleanup',  # For data retention policies
        )
    )

    class ContextTask(celery_app.Task):
        """
        Custom Celery Task class that wraps task execution in a Flask app context.
        This ensures that database connections, configurations, etc., are available
        within tasks.
        """
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app